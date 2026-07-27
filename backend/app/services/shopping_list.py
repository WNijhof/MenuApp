"""Builds a shopping list from a week's recipes plus manually-added extras.

Deliberately simple: ingredient lines are taken as-is from each recipe (no
quantity parsing/merging - source sites format quantities far too
inconsistently for that to be reliable) and only deduplicated on exact
text match. Lines matching a configured pantry staple are left off.
"""

import json

from sqlalchemy.orm import Session

from app.models import PantryStaple, ShoppingListExtra, WeekMenu
from app.services.categorizer import ingredient_matches_pantry


def build_shopping_list(db: Session, week_menu: WeekMenu) -> list[dict]:
    """Each item is {text, extra_id}. extra_id is None for recipe-derived
    items (nothing to delete - they're recomputed fresh every call) and
    set for manually-added ones (deletable via routers/shopping.py)."""
    pantry_terms = [row.term for row in db.query(PantryStaple).all()]

    seen: dict[str, str] = {}
    for day in week_menu.days:
        if not day.recipe:
            continue
        ingredients = json.loads(day.recipe.ingredients_json or "[]")
        for line in ingredients:
            line = line.strip()
            if not line:
                continue
            if pantry_terms and ingredient_matches_pantry(line, pantry_terms):
                continue
            seen.setdefault(line.lower(), line)

    items = [
        {"text": text, "extra_id": None} for text in sorted(seen.values(), key=str.lower)
    ]

    extras = db.query(ShoppingListExtra).order_by(ShoppingListExtra.created_at).all()
    items.extend({"text": e.text, "extra_id": e.id} for e in extras)

    return items
