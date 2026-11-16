"""The simple "AVG" meal (Aardappel, Groente, Vlees): instead of a recipe, a
day can be a potato + vegetable + meat combination picked from the fixed
catalog in data/avg_options.json. The choice is stored on the WeekMenuDay as
JSON ({"starch": id, "veg": id, "meat": id, "portions": n}) and expands to
plain ingredient lines for the shopping list, so it merges with recipe
ingredients ("500 g aardappelen" from here + "300 g aardappelen" from a
recipe -> "800 g aardappelen")."""

import json
import math
import random
from functools import lru_cache
from pathlib import Path

CATALOG_PATH = Path(__file__).resolve().parent.parent / "data" / "avg_options.json"
CATEGORIES = ("starch", "veg", "meat")
DEFAULT_PORTIONS = 2
MAX_PORTIONS = 12


@lru_cache(maxsize=1)
def catalog() -> dict[str, list[dict]]:
    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return {category: raw[category] for category in CATEGORIES}


def _option(category: str, option_id: str) -> dict | None:
    return next((o for o in catalog()[category] if o["id"] == option_id), None)


def is_valid(choice: dict) -> bool:
    portions = choice.get("portions")
    return (
        all(_option(category, choice.get(category)) for category in CATEGORIES)
        and isinstance(portions, int)
        and 1 <= portions <= MAX_PORTIONS
    )


def random_choice(portions: int = DEFAULT_PORTIONS) -> dict:
    choice = {category: random.choice(catalog()[category])["id"] for category in CATEGORIES}
    choice["portions"] = portions
    return choice


def parse(avg_json: str | None) -> dict | None:
    """The stored choice, or None when the day isn't an AVG meal or the
    catalog no longer has one of its options (catalog edited since)."""
    if not avg_json:
        return None
    try:
        choice = json.loads(avg_json)
    except ValueError:
        return None
    return choice if isinstance(choice, dict) and is_valid(choice) else None


def shopping_lines(choice: dict, lang: str) -> list[str]:
    """One ingredient line per component, quantities scaled by portions."""
    lines = []
    for category in CATEGORIES:
        option = _option(category, choice[category])
        name = option["shop"].get(lang) or option["shop"]["en"]
        amount = option["per_person"] * choice["portions"]
        if option["unit"]:
            lines.append(f"{round(amount)} {option['unit']} {name}")
        else:
            lines.append(f"{max(1, math.ceil(amount))} {name}")
    return lines
