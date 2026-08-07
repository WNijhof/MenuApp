"""Builds a shopping list from a week's recipes plus manually-added extras.

Deliberately simple: ingredient lines are taken as-is from each recipe (no
quantity parsing/merging - source sites format quantities far too
inconsistently for that to be reliable) and only deduplicated on exact
text match (after translation - see below). Lines matching a configured
pantry staple are left off.

Ingredient lines are translated to the current UI language regardless of
which language the recipe itself is written in (Recipe.language), so a
Dutch and an English recipe in the same week both show up in one
consistent language on the list. Pantry-staple matching runs against the
*translated* text, since the user's own pantry terms are typed in the UI
language they see - matching the untranslated source text would miss a
Dutch recipe's "zout" against a pantry staple typed as "salt" in an
English-language household, or vice versa.
"""

import json

from sqlalchemy.orm import Session

from app.models import PantryStaple, ShoppingListExtra, WeekMenu
from app.services.categorizer import ingredient_matches_pantry
from app.services.settings import get_language
from app.services.translator import translate_lines


def build_shopping_list(db: Session, week_menu: WeekMenu) -> list[dict]:
    """Each item is {text, extra_id}. extra_id is None for recipe-derived
    items (nothing to delete - they're recomputed fresh every call) and
    set for manually-added ones (deletable via routers/shopping.py)."""
    ui_lang = get_language(db)
    pantry_terms = [row.term for row in db.query(PantryStaple).all()]

    # Collected in display order, grouped by the recipe's own language so
    # each distinct language pair is translated in one batch (see
    # translator.translate_lines) instead of one API call per line.
    ordered_lines: list[tuple[str, str]] = []  # (line, recipe_lang)
    lines_by_recipe_lang: dict[str, list[str]] = {}
    for day in week_menu.days:
        if not day.recipe:
            continue
        recipe_lang = day.recipe.language or "nl"
        for line in json.loads(day.recipe.ingredients_json or "[]"):
            line = line.strip()
            if not line:
                continue
            ordered_lines.append((line, recipe_lang))
            lines_by_recipe_lang.setdefault(recipe_lang, []).append(line)

    translated_by_lang = {
        recipe_lang: translate_lines(db, lines, recipe_lang, ui_lang)
        for recipe_lang, lines in lines_by_recipe_lang.items()
    }

    seen: dict[str, str] = {}
    for line, recipe_lang in ordered_lines:
        display = translated_by_lang[recipe_lang].get(line, line)
        if pantry_terms and ingredient_matches_pantry(display, pantry_terms):
            continue
        seen.setdefault(display.lower(), display)

    items = [
        {"text": text, "extra_id": None} for text in sorted(seen.values(), key=str.lower)
    ]

    extras = db.query(ShoppingListExtra).order_by(ShoppingListExtra.created_at).all()
    items.extend({"text": e.text, "extra_id": e.id} for e in extras)

    return items
