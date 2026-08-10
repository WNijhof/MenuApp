"""Builds the 7-day menu: random recipes, spread across dish types so the
week isn't e.g. pasta every night, honoring the configured exclusions."""

import datetime
import json
import random
from collections import defaultdict

from sqlalchemy.orm import Session

from app.i18n import t
from app.models import ExclusionRule, Leftover, Offer, Recipe, WeekMenu, WeekMenuDay
from app.services.categorizer import (
    normalize_offer_terms,
    normalize_terms,
    normalize_text,
    recipe_matches_exclusions,
    recipe_matches_offers,
)

DAYS_PER_WEEK = 7
DEFAULT_COURSE_COUNTS = {"hoofdgerecht": DAYS_PER_WEEK}

# How many past weeks a used recipe stays out of rotation before it's
# eligible again - long enough that a new week doesn't just replay the
# previous one, short enough that a modest recipe collection doesn't run
# dry. Liked recipes are exempt from this cooldown entirely (see
# _select_recipes_for_course / refresh_day): a thumbs-up lets a recipe
# come back sooner, on equal footing with never-recently-used ones, not
# with priority over them.
RECENT_WEEKS_COOLDOWN = 3


def _recently_used_recipe_ids(
    db: Session, before_date: datetime.date, weeks: int = RECENT_WEEKS_COOLDOWN
) -> set[int]:
    """Recipe ids used in the `weeks` WeekMenus immediately preceding
    `before_date` (regenerating the same week doesn't count against
    itself, since only strictly earlier weeks are considered)."""
    recent_week_ids = [
        row.id
        for row in db.query(WeekMenu.id)
        .filter(WeekMenu.week_start_date < before_date)
        .order_by(WeekMenu.week_start_date.desc())
        .limit(weeks)
        .all()
    ]
    if not recent_week_ids:
        return set()
    rows = (
        db.query(WeekMenuDay.recipe_id)
        .filter(WeekMenuDay.week_menu_id.in_(recent_week_ids))
        .filter(WeekMenuDay.recipe_id.isnot(None))
        .all()
    )
    return {row[0] for row in rows}


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
    """Recipes that use up a tracked leftover, or an ingredient currently
    on offer, get weighted preference during selection - liked recipes
    deliberately do NOT: a thumbs-up only exempts a recipe from the
    recent-use cooldown (see _recently_used_recipe_ids / recent_ids
    below), it doesn't make it more likely to be picked than an equally
    fresh candidate. Offer/leftover matching reuses the same literal
    term-match either way - a discounted product name is just another
    kind of "prefer this if you can" term, not a taxonomy category. Terms
    are pre-normalized once outside the loop: with hundreds of offers,
    re-normalizing them on every single recipe check would dominate the
    runtime (measured ~5x speedup for offers)."""
    leftover_terms = normalize_terms([row.term for row in db.query(Leftover).all()])
    offer_terms = normalize_offer_terms([row.name for row in db.query(Offer).all()])
    preferred = set()
    for r in recipes:
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
    recent_ids: set[int],
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

    def _eligible(pool: list[Recipe]) -> list[Recipe]:
        # A recipe is eligible if it hasn't been used elsewhere this week,
        # and either falls outside the recent-use cooldown or is liked -
        # a thumbs-up exempts it from the cooldown, but doesn't otherwise
        # change its odds against fresh, never-recently-used candidates.
        return [
            r for r in pool if r.id not in used_ids and (r.id not in recent_ids or r.rating == "like")
        ]

    used_ids: set[int] = set()
    chosen_list: list[Recipe] = []
    for slot_index, dish_type in enumerate(sequence):
        candidates = _eligible(pool_by_type[dish_type])
        if not candidates:
            # Ran out of eligible recipes for this type this week - borrow
            # from any other type instead of leaving the slot empty.
            candidates = _eligible(recipes)
        if not candidates:
            # Nothing eligible left unused this week at all - borrow a
            # repeat (even outside the cooldown) rather than leaving the
            # slot empty.
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
    db: Session,
    course_counts: dict[str, int] | None = None,
    lang: str = "en",
    week_start_date: datetime.date | None = None,
) -> tuple[list[Recipe | None], list[str]]:
    """Returns (7 recipes-or-None in day order, warnings). `week_start_date`
    anchors the recent-use cooldown - pass the week being generated so
    only earlier weeks count against it."""
    course_counts = course_counts or DEFAULT_COURSE_COUNTS
    warnings: list[str] = []
    available = get_available_recipes(db)

    if not available:
        return [None] * DAYS_PER_WEEK, [t("no_recipes_available", lang)]

    preferred_ids = _preferred_recipe_ids(db, available)
    recent_ids = _recently_used_recipe_ids(db, week_start_date) if week_start_date else set()

    course_pool: dict[str, list[Recipe]] = {}
    for course, count in course_counts.items():
        recipes_for_course = [r for r in available if r.course == course]
        course_pool[course] = _select_recipes_for_course(
            recipes_for_course, count, preferred_ids, recent_ids, warnings, course, lang
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

    selection, warnings = generate_week_selection(db, course_counts, lang, week_start_date)

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


def _recipe_matches_query(recipe: Recipe, query_words: list[str]) -> bool:
    """A loose "does this recipe look like what the user typed" check
    (e.g. 'lasagne', 'gehaktbal') against title/keywords/cuisine - the same
    freeform fields a recipe's own site would use, unlike dish_type which
    is too coarse-grained for a specific dish name. All words must appear
    (as a substring, so Dutch compounds/plurals still match) - AND rather
    than OR, so a two-word query like 'kip curry' doesn't match every
    recipe that merely contains chicken."""
    text = normalize_text(" ".join(filter(None, [recipe.title, recipe.keywords, recipe.cuisine])))
    return all(word in text for word in query_words)


def refresh_day(
    db: Session, week_menu: WeekMenu, day_of_week: int, lang: str = "en", query: str | None = None
) -> tuple[WeekMenuDay, str | None]:
    """Swap the recipe on one day for a different pick of the same course.
    Without `query`, picks randomly, preferring a dish type that differs
    from the neighbouring days (as before). With `query` (e.g. 'lasagne',
    'gehaktbal'), narrows the candidate pool to recipes whose title/
    keywords/cuisine match it - a deliberate, specific request, so unlike
    the random path it also ignores the recent-use cooldown: a user typing
    a dish name wants that dish, not to be told it's too soon to repeat it,
    and the match itself is often narrow enough that the cooldown would
    leave nothing to pick from at all."""
    day_row = next(d for d in week_menu.days if d.day_of_week == day_of_week)
    target_course = day_row.recipe.course if day_row.recipe else "hoofdgerecht"

    available = get_available_recipes(db)
    same_course = [r for r in available if r.course == target_course]

    query_words = [w for w in normalize_text(query).split() if w] if query else []
    if query_words:
        same_course = [r for r in same_course if _recipe_matches_query(r, query_words)]
        if not same_course:
            return day_row, t("no_recipe_matches_query", lang, query=query.strip())
    elif not same_course:
        warning = t("no_other_recipes_for_course", lang, course=target_course)
        return day_row, warning

    preferred_ids = _preferred_recipe_ids(db, available)
    recent_ids = set() if query_words else _recently_used_recipe_ids(db, week_menu.week_start_date)

    used_recipe_ids = {d.recipe_id for d in week_menu.days if d.recipe_id}
    used_recipe_ids.discard(day_row.recipe_id)

    neighbour_types = set()
    for neighbour_index in (day_of_week - 1, day_of_week + 1):
        neighbour = next((d for d in week_menu.days if d.day_of_week == neighbour_index), None)
        if neighbour and neighbour.recipe:
            neighbour_types.add(neighbour.recipe.dish_type)

    # Same eligibility rule as the main generator: not used elsewhere this
    # week, and either outside the recent-use cooldown or liked (a
    # thumbs-up exempts it from the cooldown without otherwise boosting
    # its odds against equally-fresh candidates).
    eligible = [
        r
        for r in same_course
        if r.id not in used_recipe_ids and (r.id not in recent_ids or r.rating == "like")
    ]
    best = [r for r in eligible if r.dish_type not in neighbour_types]

    warning = None
    if best:
        chosen = _pick_preferred(best, preferred_ids)
    elif eligible:
        chosen = _pick_preferred(eligible, preferred_ids)
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
