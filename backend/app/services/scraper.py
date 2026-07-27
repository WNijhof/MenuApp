"""Site-agnostic recipe discovery: find candidate recipe URLs on a site via
its sitemap(s), then parse each with the generic schema.org parser. No
per-site scraping code is needed as long as the site publishes Recipe
JSON-LD, which the vast majority of recipe sites do.
"""

import datetime
import json
import time
import urllib.robotparser
from urllib.parse import urljoin, urlparse
from xml.etree import ElementTree

import requests
from bs4 import BeautifulSoup
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import (
    REQUEST_DELAY_SECONDS,
    REQUEST_TIMEOUT_SECONDS,
    STALE_AFTER_DAYS,
    USER_AGENT,
)
from app.models import Recipe, Source
from app.services.categorizer import infer_course, infer_dish_type
from app.services.lekkerensimpel_parser import parse_lekkerensimpel_recipe
from app.services.recipe_parser import parse_recipe

HEADERS = {"User-Agent": USER_AGENT}

_XML_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

# Per-domain fallback parsers for the rare site with no schema.org Recipe
# data at all (see lekkerensimpel_parser.py for why this one exception
# exists). Keep this map empty by default - it's not the pattern to reach
# for when a new source scrapes at 0.
_DOMAIN_FALLBACK_PARSERS = {
    "lekkerensimpel.com": parse_lekkerensimpel_recipe,
    "www.lekkerensimpel.com": parse_lekkerensimpel_recipe,
}


def _parse_with_fallbacks(url: str, html: str) -> dict | None:
    parsed = parse_recipe(url, html)
    if parsed:
        return parsed
    fallback = _DOMAIN_FALLBACK_PARSERS.get(urlparse(url).netloc.lower())
    return fallback(url, html) if fallback else None


def _root_url(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


def _fetch(url: str, as_text=True):
    resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT_SECONDS)
    resp.raise_for_status()
    return resp.text if as_text else resp.content


def _sitemap_urls_from_robots(base_url: str) -> list[str]:
    robots_url = urljoin(_root_url(base_url), "/robots.txt")
    try:
        text = _fetch(robots_url)
    except requests.RequestException:
        return []
    found = []
    for line in text.splitlines():
        if line.lower().startswith("sitemap:"):
            found.append(line.split(":", 1)[1].strip())
    return found


_robots_cache: dict[str, urllib.robotparser.RobotFileParser] = {}


def _get_robots_parser(base_url: str) -> urllib.robotparser.RobotFileParser | None:
    root = _root_url(base_url)
    if root in _robots_cache:
        return _robots_cache[root]

    parser = urllib.robotparser.RobotFileParser()
    try:
        # Fetch with our own User-Agent via requests: RobotFileParser.read()
        # uses urllib internally with no custom UA, and many sites 403 the
        # default urllib UA, which robotparser then misreads as "disallow
        # all" for everyone.
        text = _fetch(urljoin(root, "/robots.txt"))
        parser.parse(text.splitlines())
    except requests.RequestException:
        parser = None
    _robots_cache[root] = parser
    return parser


def _is_allowed(base_url: str, target_url: str) -> bool:
    parser = _get_robots_parser(base_url)
    if parser is None:
        return True
    try:
        return parser.can_fetch(USER_AGENT, target_url)
    except Exception:
        return True


def _parse_sitemap_xml(xml_bytes: bytes) -> tuple[list[str], list[str]]:
    """Returns (page_urls, nested_sitemap_urls)."""
    try:
        root = ElementTree.fromstring(xml_bytes)
    except ElementTree.ParseError:
        return [], []

    tag = root.tag.lower()
    pages = []
    nested = []
    if tag.endswith("sitemapindex"):
        for sitemap_el in root.findall("sm:sitemap", _XML_NS) or root.findall("sitemap"):
            loc = sitemap_el.find("sm:loc", _XML_NS)
            if loc is None:
                loc = sitemap_el.find("loc")
            if loc is not None and loc.text:
                nested.append(loc.text.strip())
    elif tag.endswith("urlset"):
        for url_el in root.findall("sm:url", _XML_NS) or root.findall("url"):
            loc = url_el.find("sm:loc", _XML_NS)
            if loc is None:
                loc = url_el.find("loc")
            if loc is not None and loc.text:
                pages.append(loc.text.strip())
    return pages, nested



# Match only the URL path, not the whole URL: many Dutch recipe sites have
# "recept(en)" in their *domain name*, which would otherwise make every
# sitemap/page match the hint.
_RECIPE_HINT_WORDS = ("recipe", "recept", "gerecht")


def _is_recipe_hinted(url: str) -> bool:
    """True if a path *segment* (not just any substring of the full path)
    starts with a recipe hint word. A substring check on the whole path
    would also match article slugs that merely mention recipes in passing
    (e.g. "/populair/mijn-recepten-nu-ook-voor-android"), which isn't a
    recipe page itself."""
    segments = urlparse(url).path.lower().split("/")
    return any(seg.startswith(h) for seg in segments for h in _RECIPE_HINT_WORDS)


# Hard ceiling on how many sitemap *index* files we'll fetch while searching
# for recipe-hinted pages, independent of max_pages (which caps final recipe
# *page* fetches). Without this, a site whose sitemap tree is huge and
# genuinely has zero recipe pages would make us walk the whole tree.
_MAX_SITEMAPS_TO_SCAN = 200


def discover_candidate_urls(source: Source, max_pages: int) -> list[str]:
    sitemap_seeds = []
    if source.sitemap_url:
        sitemap_seeds.append(source.sitemap_url)
    else:
        sitemap_seeds.extend(_sitemap_urls_from_robots(source.base_url))
        sitemap_seeds.append(urljoin(_root_url(source.base_url), "/sitemap.xml"))
        sitemap_seeds.append(urljoin(_root_url(source.base_url), "/sitemap_index.xml"))

    seen_sitemaps: set[str] = set()
    page_urls: list[str] = []
    hinted_count = 0
    to_process = list(dict.fromkeys(sitemap_seeds))  # de-dupe, keep order

    while (
        to_process
        and hinted_count < max_pages
        and len(seen_sitemaps) < _MAX_SITEMAPS_TO_SCAN
    ):
        sitemap_url = to_process.pop(0)
        if sitemap_url in seen_sitemaps:
            continue
        seen_sitemaps.add(sitemap_url)
        try:
            xml_bytes = _fetch(sitemap_url, as_text=False)
        except requests.RequestException:
            continue

        pages, nested = _parse_sitemap_xml(xml_bytes)
        page_urls.extend(pages)
        hinted_count += sum(1 for u in pages if _is_recipe_hinted(u))

        if nested:
            # Prefer nested sitemaps whose own name hints at recipes, so we
            # don't waste the sitemap-scan budget on unrelated site sections
            # (news, products, ...) when the site organizes its sitemap by
            # content type.
            hinted = [u for u in nested if _is_recipe_hinted(u)]
            rest = [u for u in nested if u not in hinted]
            to_process = hinted + rest + to_process

        time.sleep(REQUEST_DELAY_SECONDS)

    # Some sites (e.g. a single flat sitemap mixing thousands of articles
    # with recipes) never split content into hinted vs. unhinted sitemaps,
    # so the page budget would otherwise get spent on whatever happens to
    # sort first. Rank hinted page URLs first so real recipe pages aren't
    # crowded out by unrelated content within max_pages.
    deduped = list(dict.fromkeys(page_urls))
    hinted_pages = [u for u in deduped if _is_recipe_hinted(u)]
    other_pages = [u for u in deduped if not _is_recipe_hinted(u)]
    return (hinted_pages + other_pages)[:max_pages]


def _extract_recipe_hinted_links(base_url: str, html: str) -> list[str]:
    """Same-domain links from a page, filtered to recipe-hinted paths. Used
    as a fallback when a sitemap only lists category/listing pages (or no
    sitemap exists at all): if a hinted page doesn't parse as a Recipe, it's
    probably a listing page, so its own links are a reasonable place to keep
    looking without needing site-specific code.

    Query strings are dropped entirely rather than just deduped: a faceted
    search/filter widget on a category page can turn into a combinatorial
    explosion of near-identical "?ep_filter_x=y&ep_filter_a=b..." URLs for
    the same underlying listing page, each of which re-renders the same
    widget and yields yet more filter-URL variants - that can fill the
    entire crawl budget without ever reaching a real recipe page. Individual
    recipe permalinks are essentially never query-string-based, so this
    heuristic costs nothing on sites that don't have this problem."""
    root = _root_url(base_url)
    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception:  # noqa: BLE001 - malformed HTML shouldn't kill the sync
        return []
    links = []
    for a in soup.find_all("a", href=True):
        absolute = urljoin(base_url, a["href"]).split("#")[0]
        parsed = urlparse(absolute)
        if parsed.scheme not in ("http", "https") or _root_url(absolute) != root:
            continue
        if parsed.query:
            continue
        if _is_recipe_hinted(absolute):
            links.append(absolute)
    return links


# Safety cap on how many distinct URLs the link-crawl fallback may ever
# enqueue for one sync, independent of max_pages (which caps actual page
# *fetches*) - bounds memory/dedup-set growth on a site with a huge,
# heavily cross-linked category tree.
_MAX_CRAWL_QUEUE_SIZE = 5000


def sync_source(db: Session, source: Source) -> tuple[int, int, int, str | None]:
    """Crawl a source's sitemap(s), insert any new recipe pages found, and
    re-fetch existing ones older than STALE_AFTER_DAYS.

    Returns (pages_checked, recipes_new, recipes_updated, error).
    """
    try:
        candidate_urls = discover_candidate_urls(source, source.max_pages)
    except Exception as exc:  # noqa: BLE001 - surface any discovery failure
        return 0, 0, 0, f"Kon sitemap niet lezen: {exc}"

    sitemap_was_empty = not candidate_urls
    if sitemap_was_empty:
        # No sitemap (or an empty one) - fall back to crawling from the
        # source's own homepage instead of giving up immediately.
        candidate_urls = [source.base_url]

    # Recipe.url is globally unique (not just within one source), so the
    # "already have this" check has to be global too - scoping it to
    # source_id let two sources whose crawls overlap the same URL both try
    # to insert it, and the resulting IntegrityError on commit used to take
    # down the *entire* sync (see the try/except around the insert below).
    existing_recipes_by_url: dict[str, Recipe] = {row.url: row for row in db.query(Recipe).all()}
    stale_cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=STALE_AFTER_DAYS)

    pages_checked = 0
    recipes_new = 0
    recipes_updated = 0

    # A stack (not a queue): newly-discovered links from an unparsed hinted
    # page are pushed on top and explored next, depth-first. This reaches
    # real recipe leaf pages after only a few "wasted" listing-page fetches,
    # instead of breadth-first-scanning the entire category tree first.
    stack = list(reversed(candidate_urls))
    seen_urls = set(candidate_urls)
    # The seed URLs (sitemap results, or the homepage fallback) are always
    # worth following links from even when unhinted - e.g. a source's
    # homepage itself rarely has "recept" in its path. Further-discovered
    # links only get followed when they're hint-matched, or crawling would
    # never stop at the site's edges.
    seed_urls = set(candidate_urls)

    while stack and pages_checked < source.max_pages:
        url = stack.pop()
        existing = existing_recipes_by_url.get(url)
        if existing is not None:
            is_own_stale = existing.source_id == source.id and existing.scraped_at < stale_cutoff
            if not is_own_stale:
                continue
        if not _is_allowed(source.base_url, url):
            continue

        pages_checked += 1
        try:
            html = _fetch(url)
        except requests.RequestException:
            time.sleep(REQUEST_DELAY_SECONDS)
            continue

        parsed = _parse_with_fallbacks(url, html)
        time.sleep(REQUEST_DELAY_SECONDS)
        if not parsed:
            should_follow = url in seed_urls or _is_recipe_hinted(url)
            if should_follow and len(seen_urls) < _MAX_CRAWL_QUEUE_SIZE:
                for link in _extract_recipe_hinted_links(url, html):
                    if link not in seen_urls:
                        seen_urls.add(link)
                        stack.append(link)
            continue

        dish_type = infer_dish_type(
            parsed["title"], parsed["category"], parsed["keywords"], parsed["ingredients"]
        )
        course = infer_course(parsed["title"], parsed["category"], parsed["keywords"])

        # The page's own canonical URL can differ from the crawled URL
        # (redirects, trailing slashes, ...) - re-check against that too so
        # a canonical collision with a recipe already owned by *any*
        # source (url is globally unique) updates in place instead of
        # hitting the unique constraint on commit.
        target = existing if existing is not None else existing_recipes_by_url.get(parsed["url"])
        is_update = target is not None

        if not is_update:
            target = Recipe(source_id=source.id, url=parsed["url"])
            db.add(target)

        target.title = parsed["title"]
        target.image_url = parsed["image_url"]
        target.dish_type = dish_type
        target.course = course
        target.cuisine = parsed["cuisine"]
        target.keywords = parsed["keywords"]
        target.ingredients_json = json.dumps(parsed["ingredients"])
        target.instructions_json = json.dumps(parsed["instructions"])
        target.prep_time_minutes = parsed["prep_time_minutes"]
        target.cook_time_minutes = parsed["cook_time_minutes"]
        target.total_time_minutes = parsed["total_time_minutes"]
        target.servings = parsed["servings"]
        target.scraped_at = datetime.datetime.utcnow()

        try:
            db.commit()
        except IntegrityError:
            # Another recipe already owns this URL - e.g. reached via two
            # different links within this same crawl. Skip it rather than
            # losing every recipe already committed so far in this sync
            # (a single end-of-run commit used to make one collision like
            # this discard the whole batch).
            db.rollback()
            continue

        existing_recipes_by_url[parsed["url"]] = target
        if is_update:
            recipes_updated += 1
        else:
            recipes_new += 1

    if sitemap_was_empty and recipes_new == 0 and recipes_updated == 0:
        # No sitemap to begin with, and the homepage-crawl fallback didn't
        # turn up anything real either.
        return (
            pages_checked,
            recipes_new,
            recipes_updated,
            "Geen recepten-URL's gevonden via sitemap.xml / robots.txt",
        )
    return pages_checked, recipes_new, recipes_updated, None


def fetch_single_recipe(url: str) -> dict | None:
    html = _fetch(url)
    parsed = _parse_with_fallbacks(url, html)
    if not parsed:
        return None
    parsed["dish_type"] = infer_dish_type(
        parsed["title"], parsed["category"], parsed["keywords"], parsed["ingredients"]
    )
    parsed["course"] = infer_course(parsed["title"], parsed["category"], parsed["keywords"])
    return parsed
