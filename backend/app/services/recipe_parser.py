"""Generic schema.org/Recipe extraction from any recipe page.

Most recipe websites embed a JSON-LD <script type="application/ld+json">
block describing the page as a schema.org Recipe. This parser looks for
that block so we don't need site-specific scraping code.
"""

import json
import re

from bs4 import BeautifulSoup

_DURATION_RE = re.compile(
    r"P(?:(?P<days>\d+)D)?T?(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?"
)


def parse_iso8601_duration_minutes(value: str | None) -> int | None:
    if not value or not isinstance(value, str):
        return None
    match = _DURATION_RE.match(value.strip())
    if not match:
        return None
    days = int(match.group("days") or 0)
    hours = int(match.group("hours") or 0)
    minutes = int(match.group("minutes") or 0)
    total = days * 24 * 60 + hours * 60 + minutes
    return total or None


def _first_str(value):
    if value is None:
        return None
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, list) and value:
        return _first_str(value[0])
    if isinstance(value, dict):
        return _first_str(value.get("name") or value.get("url"))
    return None


def _extract_image(value):
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, list) and value:
        return _extract_image(value[0])
    if isinstance(value, dict):
        return value.get("url")
    return None


def _extract_ingredients(recipe_obj) -> list[str]:
    raw = recipe_obj.get("recipeIngredient") or recipe_obj.get("ingredients") or []
    if isinstance(raw, str):
        raw = [raw]
    result = []
    for item in raw:
        if isinstance(item, str):
            text = item.strip()
            if text:
                result.append(text)
    return result


def _extract_instructions(recipe_obj) -> list[str]:
    raw = recipe_obj.get("recipeInstructions")
    if not raw:
        return []
    steps = []
    if isinstance(raw, str):
        text = BeautifulSoup(raw, "lxml").get_text("\n").strip()
        steps = [line.strip() for line in text.split("\n") if line.strip()]
    elif isinstance(raw, list):
        for item in raw:
            if isinstance(item, str):
                text = item.strip()
                if text:
                    steps.append(text)
            elif isinstance(item, dict):
                item_type = item.get("@type", "")
                if item_type == "HowToSection":
                    inner = item.get("itemListElement") or []
                    for sub in inner:
                        text = _first_str(
                            sub.get("text") if isinstance(sub, dict) else sub
                        )
                        if text:
                            steps.append(text)
                else:
                    text = item.get("text") or _first_str(item)
                    if text:
                        steps.append(text.strip())
    return steps


def _extract_language_hint(recipe_obj) -> str | None:
    """schema.org's `inLanguage` (e.g. 'en-US', 'nl') as a bare 2-letter
    code, when it's one this app actually supports - an explicit signal
    from the site itself, preferred over guessing (see
    language_detect.resolve_language)."""
    raw = _first_str(recipe_obj.get("inLanguage"))
    if not raw:
        return None
    code = raw.strip().lower().split("-")[0]
    return code if code in ("nl", "en") else None


def _extract_keywords(recipe_obj) -> str | None:
    kw = recipe_obj.get("keywords")
    if isinstance(kw, list):
        return ", ".join(str(k) for k in kw)
    if isinstance(kw, str):
        return kw
    return None


def _walk_for_recipe(node):
    """Depth-first search through a JSON-LD blob for a Recipe object."""
    if isinstance(node, dict):
        node_type = node.get("@type")
        types = node_type if isinstance(node_type, list) else [node_type]
        if node_type and "Recipe" in types:
            return node
        if "@graph" in node:
            found = _walk_for_recipe(node["@graph"])
            if found:
                return found
        for value in node.values():
            if isinstance(value, (dict, list)):
                found = _walk_for_recipe(value)
                if found:
                    return found
    elif isinstance(node, list):
        for item in node:
            found = _walk_for_recipe(item)
            if found:
                return found
    return None


def extract_recipe_jsonld(html: str) -> dict | None:
    """Return the raw schema.org Recipe dict embedded in the page, if any."""
    soup = BeautifulSoup(html, "lxml")
    for script in soup.find_all("script", type="application/ld+json"):
        raw = script.string or script.get_text()
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            continue
        recipe = _walk_for_recipe(data)
        if recipe:
            return recipe
    return None


def parse_recipe(url: str, html: str) -> dict | None:
    """Parse a recipe page into a normalized dict, or None if not a recipe."""
    recipe_obj = extract_recipe_jsonld(html)
    if not recipe_obj:
        return None

    title = _first_str(recipe_obj.get("name"))
    if not title:
        return None

    ingredients = _extract_ingredients(recipe_obj)
    if not ingredients:
        # Not usable for exclusion matching or menu building.
        return None

    return {
        "url": url,
        "title": title,
        "image_url": _extract_image(recipe_obj.get("image")),
        "cuisine": _first_str(recipe_obj.get("recipeCuisine")),
        "category": _first_str(recipe_obj.get("recipeCategory")),
        "keywords": _extract_keywords(recipe_obj),
        "language_hint": _extract_language_hint(recipe_obj),
        "ingredients": ingredients,
        "instructions": _extract_instructions(recipe_obj),
        "prep_time_minutes": parse_iso8601_duration_minutes(
            recipe_obj.get("prepTime")
        ),
        "cook_time_minutes": parse_iso8601_duration_minutes(
            recipe_obj.get("cookTime")
        ),
        "total_time_minutes": parse_iso8601_duration_minutes(
            recipe_obj.get("totalTime")
        ),
        "servings": _first_str(recipe_obj.get("recipeYield")),
    }
