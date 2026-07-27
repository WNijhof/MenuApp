"""Fetches current weekly offers from supermarket chains.

All three supported stores (Aldi, Jumbo, Lidl) are fetched through the
same third-party channel, supermarktaanbiedingen.com, rather than each
store's own site: Aldi's own site is scrapable directly (see git history
for that version), but Jumbo's price data is buried in a Nuxt.js
"devalue"-serialized blob that needs its own decoder, and Lidl's offers
listing is client-rendered with no server-side data at all regardless of
User-Agent (same class of problem as the PLUS/Coop recipe sources). The
aggregator site sidesteps all three problems at once: it renders a plain
server-side HTML card per offer, per store, with a consistent structure.

Trade-off: no reliable per-offer validity date on this channel (unlike
Aldi's own site, which had one) - the date text on the page isn't
consistently attached to individual cards, so `valid_until` is always
None here. Not worth chasing for what it's used for (a preference nudge
during menu generation, not a "this offer has expired" check).
"""

import re

from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from app.models import Offer
from app.services.scraper import _fetch

AGGREGATOR_BASE_URL = "https://www.supermarktaanbiedingen.com"
SUPPORTED_STORES = ["aldi", "jumbo", "lidl"]

_PRICE_RE = re.compile(r"^\d+[.,]\d+$")


def _parse_price(text: str | None) -> float | None:
    if not text:
        return None
    text = text.strip()
    if not _PRICE_RE.match(text):
        return None
    return float(text.replace(",", "."))


def _card_text(card, class_name: str) -> str | None:
    el = card.find(class_=class_name)
    return el.get_text(strip=True) if el else None


def fetch_store_offers(store: str) -> list[dict]:
    html = _fetch(f"{AGGREGATOR_BASE_URL}/aanbiedingen/{store}")
    soup = BeautifulSoup(html, "lxml")

    offers = []
    for index, card in enumerate(soup.find_all(class_="card")):
        title_el = card.find(class_="card_title")
        link_el = card.find(class_="product-title")
        if not title_el or not link_el:
            continue
        name = title_el.get_text(strip=True)
        if not name:
            continue

        href = (link_el.get("href") or "").rstrip("/")
        slug = href.rsplit("/", 1)[-1] if href else ""
        external_id = slug or f"{name}-{index}"

        price_text = _card_text(card, "card_prijs")
        old_price_text = _card_text(card, "card_prijs-oud")

        price = _parse_price(price_text)
        original_price = _parse_price(old_price_text)

        if price is not None and original_price:
            discount_label = f"-{round((1 - price / original_price) * 100)}%"
        elif price is None:
            # card_prijs held descriptive text instead of a number, e.g.
            # "20% korting" or "OP=OP" - that text IS the discount label.
            discount_label = price_text
        else:
            discount_label = None

        offers.append(
            {
                "store": store,
                "external_id": external_id,
                "name": name,
                "price": price,
                "original_price": original_price,
                "discount_label": discount_label,
                "valid_until": None,
            }
        )
    return offers


def sync_store_offers(db: Session, store: str) -> int:
    """Full replace: this week's offers entirely supersede last week's,
    there's no meaningful "still valid" carry-over to preserve."""
    offers = fetch_store_offers(store)
    db.query(Offer).filter(Offer.store == store).delete()
    for entry in offers:
        db.add(Offer(**entry))
    db.commit()
    return len(offers)
