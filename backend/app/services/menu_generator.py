"""Builds the 7-day menu: random recipes, spread across dish types so the
week isn't e.g. pasta every night, honoring the configured exclusions."""

import json
import random
from collections import defaultdict

from sqlalchemy.orm import Session

from app.i18n import t
from app.models import ExclusionRule, Leftover, Offer, Recipe, WeekMenu, WeekMenuDay
from app.services.categorizer import (
    normalize_offer_terms,
    normalize_terms,
    recipe_matches_exclusions,
    recipe_matches_offers,
)

DAYS_PER_WEEK = 7
DEFAULT_COURSE_COUNTS = {"hoofdgerecht": DAYS_PER_WEEK}


def get_available_recipes(db: Session) -> list[Recipe]:
    """All recipes minus disliked ones and ingredient-exclusion matches.
    Course filtering happens separately per requested course count."""
    exclusion_terms = [row.term for row in db.query(ExclusionRule).all()]
    all_recipes = [r for r in db.query(Recipe).all() if r.rating != "dislike"]
    if not exclusion_terms:
        return all_recipes
    return [
        r
        for r in all_recipes
        if not recipe_matches_exclusions(json.loads(r.ingredients_json or "[]"), exclusion_terms)
    ]


def _preferred_recipe_ids(db: Session, recipes: list[Recipe]) -> set[int]:
    """Favorited recipes, recipes that use up a tracked leftover, and
    recipes using an ingredient currently on offer all get weighted
    preference during selection. Offer/leftover matching reuses the same
    literal term-match either way - a discounted product name is just
    another kind of "prefer this if you can" term, not a taxonomy
    category. Terms are pre-normalized once outside the loop: with
    hundreds of offers, re-normalizing them on every single recipe check
    would dominate the runtime (measured ~5x speedup for offers)."""
    leftover_terms = normalize_terms([row.term for row in db.query(Leftover).all()])
    offer_terms = normalize_offer_terms([row.name for row in db.query(Offer).all()])
    preferred = set()
    for r in recipes:
        if r.rating == "like":
            preferred.add(r.id)
            continue
        ingredients = json.loads(r.ingredients_json or "[]")
        if leftover_terms and recipe_matches_offers(ingredients, leftover_terms):
            preferred.add(r.id)
        elif offer_terms and recipe_matches_offers(ingredients, offer_terms):
            preferred.add(r.id)
    return preferred


def _pick_preferred(candidates: list[Recipe], preferred_ids: set[int]) -> Recipe:
    preferred = [r for r in candidates if r.id in preferred_ids]
    return random.choice(preferred or candidates)


def _group_by_dish_type(recipes: list[Recipe]) -> dict[str, list[Recipe]]:
    groups: dict[str, list[Recipe]] = defaultdict(list)
    for r in recipes:
        groups[r.dish_type].append(r)
    for group in groups.values():
        random.shuffle(group)
    return groups


def _build_type_sequence(dish_types: list[str], length: int) -> list[str]:
    """Round-robin over shuffled dish types so identical types are spread
    as far apart as possible instead of clustering."""
    shuffled = dish_types[:]
    random.shuffle(shuffled)
    return [shuffled[i % len(shuffled)] for i in range(length)]


def _select_recipes_for_course(
    recipes: list[Recipe],
    count: int,
    preferred_ids: set[int],
    warnings: list[str],
    course: str,
    lang: str,
) -> list[Recipe]:
    if count <= 0:
        return []
    if not recipes:
        warnings.append(t("no_recipes_for_course", lang, course=course, count=count))
        return []

    groups = _group_by_dish_type(recipes)
    dish_types = list(groups.keys())
    sequence = _build_type_sequence(dish_types, count)
    pool_by_type = {t: list(rs) for t, rs in groups.items()}

    used_ids: set[int] = set()
    chosen_list: list[Recipe] = []
    for slot_index, dish_type in enumerate(sequence):
        candidates = [r for r in pool_by_type[dish_type] if r.id not in used_ids]
        if not candidates:
            # Ran out of unused recipes for this type this week - borrow
            # from any other type instead of leaving the slot empty.
            fallback = [r for r in recipes if r.id not in used_ids]
            if not fallback:
                warnings.append(t("too_few_unique_recipes", lang, course=course))
                fallback = recipes
            candidates = fallback

        chosen = _pick_preferred(candidates, preferred_ids)
        used_ids.add(chosen.id)
        chosen_list.append(chosen)

    if len(dish_types) < 3 and count >= 3:
        warnings.append(t("low_dish_type_variety", lang, course=course))

    return chosen_list


def generate_week_selection(
    db: Session, course_counts: dict[str, int] | None = None, lang: str = "en"
) -> tuple[list[Recipe | None], list[str]]:
    """Returns (7 recipes-or-None in day order, warnings)."""
    course_counts = course_counts or DEFAULT_COURSE_COUNTS
    warnings: list[str] = []
    available = get_available_recipes(db)

    if not available:
        return [None] * DAYS_PER_WEEK, [t("no_recipes_available", lang)]

    preferred_ids = _preferred_recipe_ids(db, available)

    course_pool: dict[str, list[Recipe]] = {}
    for course, count in course_counts.items():
        recipes_for_course = [r for r in available if r.course == course]
        course_pool[course] = _select_recipes_for_course(
            recipes_for_course, count, preferred_ids, warnings, course, lang
        )

    # Interleave day order so e.g. the nagerecht doesn't always land on the
    # last day: build one shuffled label sequence covering all 7 days (with
    # None for any days left open when fewer than 7 dishes were requested),
    # then pop the next pre-selected recipe per label. Shuffling the None
    # labels in too spreads open days across the week instead of always
    # trailing at the end.
    labels: list[str | None] = [
        course for course, recipes in course_pool.items() for _ in recipes
    ]
    labels += [None] * (DAYS_PER_WEEK - len(labels))
    random.shuffle(labels)

    cursors = {course: 0 for course in course_pool}
    selection: list[Recipe | None] = []
    for label in labels:
        if label is None:
            selection.append(None)
            continue
        idx = cursors[label]
        selection.append(course_pool[label][idx])
        cursors[label] += 1

    return selection, warnings


def generate_week_menu(
    db: Session,
    week_start_date,
    course_counts: dict[str, int] | None = None,
    lang: str = "en",
    clear_leftovers: bool = True,
) -> WeekMenu:
    existing = (
        db.query(WeekMenu).filter(WeekMenu.week_start_date == week_start_date).first()
    )
    if existing:
        db.delete(existing)
        db.flush()

    selection, warnings = generate_week_selection(db, course_counts, lang)

    week_menu = WeekMenu(
        week_start_date=week_start_date,
        course_counts_json=json.dumps(course_counts or DEFAULT_COURSE_COUNTS),
    )
    db.add(week_menu)
    db.flush()

    for day_index, recipe in enumerate(selection):
        db.add(
            WeekMenuDay(
                week_menu_id=week_menu.id,
                day_of_week=day_index,
                recipe_id=recipe.id if recipe else None,
            )
        )

    # Leftovers are assumed used once a new week has been generated around
    # them (explicit product choice, not auto-detected per recipe) - but
    # only for the actual current week. Generating a *different* week
    # (planning ahead, or looking back) has nothing to do with what's in
    # the fridge right now, so leave the leftover list alone.
    if clear_leftovers:
        db.query(Leftover).delete()

    db.commit()
    db.refresh(week_menu)
    week_menu.warnings = warnings  # transient attribute, not persisted
    return week_menu


def refresh_day(
    db: Session, week_menu: WeekMenu, day_of_week: int, lang: str = "en"
) -> tuple[WeekMenuDay, str | None]:
    """Swap the recipe on one day for a different random pick of the same
    course, preferring a dish type that differs from the neighbouring
    days."""
    day_row = next(d for d in week_menu.days if d.day_of_week == day_of_week)
    target_course = day_row.recipe.course if day_row.recipe else "hoofdgerecht"

    available = get_available_recipes(db)
    same_course = [r for r in available if r.course == target_course]
    if not same_course:
        warning = t("no_other_recipes_for_course", lang, course=target_course)
        return day_row, warning

    preferred_ids = _preferred_recipe_ids(db, available)

    used_recipe_ids = {d.recipe_id for d in week_menu.days if d.recipe_id}
    used_recipe_ids.discard(day_row.recipe_id)

    neighbour_types = set()
    for neighbour_index in (day_of_week - 1, day_of_week + 1):
        neighbour = next((d for d in week_menu.days if d.day_of_week == neighbour_index), None)
        if neighbour and neighbour.recipe:
            neighbour_types.add(neighbour.recipe.dish_type)

    unused = [r for r in same_course if r.id not in used_recipe_ids]
    best = [r for r in unused if r.dish_type not in neighbour_types]

    warning = None
    if best:
        chosen = _pick_preferred(best, preferred_ids)
    elif unused:
        chosen = _pick_preferred(unused, preferred_ids)
    else:
        candidates = [r for r in same_course if r.id != day_row.recipe_id]
        if not candidates:
            candidates = same_course
        chosen = _pick_preferred(candidates, preferred_ids)
        warning = t("repetition_unavoidable", lang)

    day_row.recipe_id = chosen.id
    db.commit()
    db.refresh(day_row)
    return day_row, warning
