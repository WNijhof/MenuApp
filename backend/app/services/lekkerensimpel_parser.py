"""One-off site-specific fallback for lekkerensimpel.com.

Deliberate exception to this project's "no per-site scraping code"
principle: this site's posts carry no schema.org Recipe data at all - not
even via the WP Recipe Maker plugin it has installed (that plugin's CSS is
loaded site-wide, but the actual recipe-card markup isn't present in the
page HTML; ingredients/instructions are typed directly into the post body
as prose). Approved by the user after confirming the generic parser and a
broader sitemap/crawl fix (see scraper.py) both come back empty here.

Heuristic, not exhaustive: many posts follow a "Tijd: ... / Benodigdheden:
<ingredients> / Bereidingswijze: <steps>" convention, but this is a ~13-
year blog archive with inconsistent formatting, so a meaningful fraction of
posts won't match and are simply skipped (same behavior as any other page
the generic parser can't make sense of).
"""

import re

from bs4 import BeautifulSoup

_INGREDIENTS_HEADER = re.compile(r"^benodigdheden\b", re.IGNORECASE)
_INSTRUCTIONS_HEADER = re.compile(r"^bereidingswijze\b", re.IGNORECASE)
_TIME_LINE = re.compile(r"^tijd\b", re.IGNORECASE)
_SERVINGS_HINT = re.compile(r"(\d+)[\s/–-]*\d*\s*person", re.IGNORECASE)
_FIRST_NUMBER = re.compile(r"\d+")

# Every post has a newsletter-signup widget appended straight after the
# article body, with no other markup boundary between the two - "Laat dit
# veld leeg" is a honeypot field label from that widget and is present
# verbatim on every page, so it doubles as a reliable end-of-content marker.
_TRAILING_NOISE_MARKER = "laat dit veld leeg"


def _extract_ingredients_and_instructions(lines: list[str]) -> tuple[list[str], list[str]]:
    ingredients_start = next(
        (i for i, line in enumerate(lines) if _INGREDIENTS_HEADER.match(line)), None
    )
    instructions_start = next(
        (i for i, line in enumerate(lines) if _INSTRUCTIONS_HEADER.match(line)), None
    )
    if ingredients_start is None or instructions_start is None:
        return [], []
    if instructions_start <= ingredients_start:
        return [], []

    ingredients = [
        line for line in lines[ingredients_start + 1 : instructions_start] if line
    ]

    instructions_lines = lines[instructions_start + 1 :]
    noise_start = next(
        (
            i
            for i, line in enumerate(instructions_lines)
            if line.strip().lower() == _TRAILING_NOISE_MARKER
        ),
        len(instructions_lines),
    )
    instructions = [line for line in instructions_lines[:noise_start] if line]
    return ingredients, instructions


def _extract_minutes(lines: list[str]) -> int | None:
    time_line = next((line for line in lines if _TIME_LINE.match(line)), None)
    if not time_line:
        return None
    match = _FIRST_NUMBER.search(time_line)
    return int(match.group()) if match else None


def _extract_servings(lines: list[str]) -> str | None:
    for line in lines[:20]:  # servings hint always appears near the top
        match = _SERVINGS_HINT.search(line)
        if match:
            return match.group(0)
    return None


def parse_lekkerensimpel_recipe(url: str, html: str) -> dict | None:
    soup = BeautifulSoup(html, "lxml")
    article = soup.find("article")
    if not article:
        return None

    h1 = soup.find("h1")
    title = h1.get_text(strip=True) if h1 else None
    if not title:
        return None

    lines = [
        line.strip() for line in article.get_text("\n", strip=True).split("\n")
    ]
    ingredients, instructions = _extract_ingredients_and_instructions(lines)
    if not ingredients:
        return None

    og_image = soup.find("meta", property="og:image")
    image_url = og_image.get("content") if og_image else None

    # WordPress category/tag classes ("category-hoofdgerechten",
    # "tag-risotto") double as a keywords signal for dish-type/course
    # inference, same role `keywords`/`category` play for the generic
    # schema.org parser.
    article_classes = article.get("class") or []
    keyword_classes = [
        c.split("-", 1)[1].replace("-", " ")
        for c in article_classes
        if c.startswith("category-") or c.startswith("tag-")
    ]

    total_minutes = _extract_minutes(lines)

    return {
        "url": url,
        "title": title,
        "image_url": image_url,
        "cuisine": None,
        "category": None,
        "keywords": ", ".join(keyword_classes) or None,
        "ingredients": ingredients,
        "instructions": instructions,
        "prep_time_minutes": None,
        "cook_time_minutes": None,
        "total_time_minutes": total_minutes,
        "servings": _extract_servings(lines),
    }
