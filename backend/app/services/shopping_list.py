"""Builds a shopping list from a week's recipes plus manually-added extras.

Ingredient lines are translated to the UI language, pantry staples are left
off, and the rest is merged: lines naming the same ingredient are combined
into one item with their quantities added up ("200 g gehakt" + "300 g
gehakt" -> "500 g gehakt"; see services/ingredients.py). Lines whose
quantity can't be read stay as their own plain item. The result is ordered
in supermarket-walking order (produce first, frozen near the end, see
data/store_sections.json), each item tagged with its section.

Days marked "skip_shopping" contribute nothing (eating out, everything is
already at home, ...). Finer-grained, a day can also leave off or change
single ingredient lines (WeekMenuDay.ingredient_overrides_json, see
parse_overrides): a replacement is typed by the user in the UI language, so
it goes onto the list as-is, without translation.

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
from app.services import avg as avg_service
from app.services.categorizer import compile_terms, normalize_terms
from app.services.ingredients import (
    classify_section,
    format_item,
    merge_lines,
    parse_line,
    section_order,
)
from app.services.settings import get_language
from app.services.translator import translate_lines


def parse_overrides(raw: str | None) -> dict[str, str | None]:
    """{original line: replacement or None (= left off)}; tolerant of a
    missing or malformed value, which simply means "no overrides"."""
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except ValueError:
        return {}
    if not isinstance(data, dict):
        return {}
    return {
        str(k): (v.strip() if isinstance(v, str) and v.strip() else None)
        for k, v in data.items()
    }


def build_shopping_list(db: Session, week_menu: WeekMenu) -> list[dict]:
    """Each item is {text, extra_id, section}. extra_id is None for
    recipe-derived items (nothing to delete - they're recomputed fresh every
    call) and set for manually-added ones (deletable via
    routers/shopping.py)."""
    ui_lang = get_language(db)
    pantry_matcher = compile_terms(
        normalize_terms([row.term for row in db.query(PantryStaple).all()])
    )

    # Collected in display order, grouped by the recipe's own language so
    # each distinct language pair is translated in one batch (see
    # translator.translate_lines) instead of one API call per line.
    # recipe_lang is None for user-typed replacements (already UI language).
    ordered_lines: list[tuple[str, str | None]] = []  # (line, recipe_lang)
    lines_by_recipe_lang: dict[str, list[str]] = {}
    avg_lines: list[str] = []  # already in the UI language, nothing to translate
    for day in week_menu.days:
        if day.skip_shopping:
            continue
        choice = avg_service.parse(day.avg_json) if not day.recipe else None
        if choice:
            avg_lines.extend(avg_service.shopping_lines(choice, ui_lang))
        if not day.recipe:
            continue
        recipe_lang = day.recipe.language or "nl"
        overrides = parse_overrides(day.ingredient_overrides_json)
        for original in json.loads(day.recipe.ingredients_json or "[]"):
            line = original.strip()
            if not line:
                continue
            if original in overrides or line in overrides:
                replacement = overrides.get(original, overrides.get(line))
                if replacement:
                    ordered_lines.append((replacement, None))
                continue
            ordered_lines.append((line, recipe_lang))
            lines_by_recipe_lang.setdefault(recipe_lang, []).append(line)

    translated_by_lang = {
        recipe_lang: translate_lines(db, lines, recipe_lang, ui_lang)
        for recipe_lang, lines in lines_by_recipe_lang.items()
    }

    display_lines = []
    for line, recipe_lang in ordered_lines:
        display = translated_by_lang[recipe_lang].get(line, line) if recipe_lang else line
        if pantry_matcher.matches([display]):
            continue
        display_lines.append(display)
    display_lines.extend(line for line in avg_lines if not pantry_matcher.matches([line]))

    order = {key: i for i, key in enumerate(section_order())}
    items: list[dict] = []
    for merged in merge_lines(display_lines):
        section = classify_section(merged.name)
        items.append(
            {
                "text": format_item(merged, ui_lang),
                "extra_id": None,
                "section": section,
                "_sort": (order[section], merged.key),
            }
        )

    for extra in db.query(ShoppingListExtra).order_by(ShoppingListExtra.created_at).all():
        parsed = parse_line(extra.text)
        section = classify_section(parsed.name)
        items.append(
            {
                "text": extra.text,
                "extra_id": extra.id,
                "section": section,
                "_sort": (order[section], parsed.key),
            }
        )

    items.sort(key=lambda item: item["_sort"])
    for item in items:
        del item["_sort"]
    return items
