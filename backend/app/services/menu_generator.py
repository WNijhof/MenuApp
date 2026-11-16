"""Builds the 7-day menu: random recipes, spread across dish types so the
week isn't e.g. pasta every night, honoring the configured exclusions.

All candidate selection runs against the in-memory recipe index (see
services/recipe_index.py) rather than the Recipe table, so generating a week
or swapping a single day doesn't load and re-parse the whole collection."""

import datetime
import json
import random
from collections import defaultdict

from sqlalchemy.orm import Session

from app.i18n import t
from app.models import Leftover, WeekMenu, WeekMenuDay
from app.services import avg as avg_service
from app.services.categorizer import normalize_text
from app.services.recipe_index import (
    IndexedRecipe,
    available_recipes,
    get_index,
    preferred_recipe_ids,
)

DAYS_PER_WEEK = 7
DEFAULT_COURSE_COUNTS = {"hoofdgerecht": 5}

# How many past weeks a used recipe stays out of rotation before it's
# eligible again - long enough that a new week doesn't just replay the
# previous one, short enough that a modest recipe collection doesn't run
# dry. Liked recipes are exempt from this cooldown entirely (see
# _select_recipes_for_course / pick_replacement): a thumbs-up lets a recipe
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


def _pick_preferred(candidates: list[IndexedRecipe], preferred_ids: set[int]) -> IndexedRecipe:
    """Recipes that use up a tracked leftover get preference - liked recipes deliberately do NOT: a thumbs-up
    only exempts a recipe from the recent-use cooldown, it doesn't make it
    more likely to be picked than an equally fresh candidate."""
    preferred = [r for r in candidates if r.id in preferred_ids]
    return random.choice(preferred or candidates)


def _group_by_dish_type(recipes: list[IndexedRecipe]) -> dict[str, list[IndexedRecipe]]:
    groups: dict[str, list[IndexedRecipe]] = defaultdict(list)
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
    recipes: list[IndexedRecipe],
    count: int,
    preferred_ids: set[int],
    recent_ids: set[int],
    warnings: list[str],
    course: str,
    lang: str,
    already_used: set[int],
) -> list[IndexedRecipe]:
    if count <= 0:
        return []
    if not recipes:
        warnings.append(t("no_recipes_for_course", lang, course=course, count=count))
        return []

    groups = _group_by_dish_type(recipes)
    dish_types = list(groups.keys())
    sequence = _build_type_sequence(dish_types, count)
    pool_by_type = {dt: list(rs) for dt, rs in groups.items()}

    used_ids: set[int] = set(already_used)

    def _eligible(pool: list[IndexedRecipe]) -> list[IndexedRecipe]:
        # A recipe is eligible if it hasn't been used elsewhere this week,
        # and either falls outside the recent-use cooldown or is liked -
        # a thumbs-up exempts it from the cooldown, but doesn't otherwise
        # change its odds against fresh, never-recently-used candidates.
        return [
            r for r in pool if r.id not in used_ids and (r.id not in recent_ids or r.rating == "like")
        ]

    chosen_list: list[IndexedRecipe] = []
    for dish_type in sequence:
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


def _plan_counts(
    course_counts: dict[str, int], kept_per_course: dict[str, int], warnings: list[str], lang: str
) -> dict[str, int]:
    """Effective per-course totals once kept (pinned/cooked) days are
    accounted for: kept days count toward the requested number, and never
    disappear even when the requested number is lower than what's kept.
    If keeping them pushes the total past the 7 available days, the number
    of *new* dishes is trimmed to fit."""
    effective = {
        course: max(course_counts.get(course, 0), kept_per_course.get(course, 0))
        for course in set(course_counts) | set(kept_per_course)
    }
    trimmed = False
    while sum(effective.values()) > DAYS_PER_WEEK:
        trimmable = [c for c in effective if effective[c] > kept_per_course.get(c, 0)]
        if not trimmable:
            break
        effective[max(trimmable, key=lambda c: effective[c] - kept_per_course.get(c, 0))] -= 1
        trimmed = True
    if trimmed:
        warnings.append(t("counts_trimmed_for_kept", lang))
    return effective


def generate_week_menu(
    db: Session,
    week_start_date,
    course_counts: dict[str, int] | None = None,
    lang: str = "en",
    clear_leftovers: bool = True,
) -> WeekMenu:
    """(Re)generates a week. Days that are pinned or already ticked off as
    cooked keep their recipe and day slot; only the rest is drawn fresh."""
    course_counts = dict(course_counts or DEFAULT_COURSE_COUNTS)
    index = get_index(db)

    existing = db.query(WeekMenu).filter(WeekMenu.week_start_date == week_start_date).first()
    kept: dict[int, dict] = {}
    if existing:
        for day in existing.days:
            if not (day.pinned or day.cooked):
                continue
            is_recipe = day.recipe_id and day.recipe_id in index.by_id
            is_avg = not day.recipe_id and avg_service.parse(day.avg_json)
            if is_recipe or is_avg:
                kept[day.day_of_week] = {
                    "recipe_id": day.recipe_id,
                    "avg_json": day.avg_json if is_avg else None,
                    "pinned": day.pinned,
                    "cooked": day.cooked,
                    "skip_shopping": day.skip_shopping,
                }
        db.delete(existing)
        db.flush()

    warnings: list[str] = []
    kept_per_course: dict[str, int] = defaultdict(int)
    for info in kept.values():
        # An AVG meal is a main course.
        course = index.by_id[info["recipe_id"]].course if info["recipe_id"] else "hoofdgerecht"
        kept_per_course[course] += 1
    effective_counts = _plan_counts(course_counts, kept_per_course, warnings, lang)

    available = available_recipes(db)
    free_days = [d for d in range(DAYS_PER_WEEK) if d not in kept]
    selection: dict[int, IndexedRecipe | None] = {d: None for d in free_days}

    if not available:
        warnings.append(t("no_recipes_available", lang))
    else:
        preferred_ids = preferred_recipe_ids(db)
        recent_ids = _recently_used_recipe_ids(db, week_start_date)
        kept_ids = {info["recipe_id"] for info in kept.values() if info["recipe_id"]}

        course_pool: dict[str, list[IndexedRecipe]] = {}
        for course, total in effective_counts.items():
            needed = total - kept_per_course.get(course, 0)
            recipes_for_course = [r for r in available if r.course == course]
            course_pool[course] = _select_recipes_for_course(
                recipes_for_course, needed, preferred_ids, recent_ids, warnings, course, lang, kept_ids
            )

        # Interleave day order so e.g. the nagerecht doesn't always land on
        # the last free day: one shuffled label sequence covering every free
        # day (None for days left open when fewer dishes were requested),
        # then pop the next pre-selected recipe per label.
        labels: list[str | None] = [
            course for course, recipes in course_pool.items() for _ in recipes
        ]
        labels += [None] * (len(free_days) - len(labels))
        random.shuffle(labels)

        cursors = {course: 0 for course in course_pool}
        for day_index, label in zip(free_days, labels):
            if label is None:
                continue
            selection[day_index] = course_pool[label][cursors[label]]
            cursors[label] += 1

    week_menu = WeekMenu(
        week_start_date=week_start_date,
        course_counts_json=json.dumps(effective_counts),
    )
    db.add(week_menu)
    db.flush()

    for day_index in range(DAYS_PER_WEEK):
        if day_index in kept:
            info = kept[day_index]
            db.add(WeekMenuDay(week_menu_id=week_menu.id, day_of_week=day_index, **info))
        else:
            recipe = selection[day_index]
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


def _recipe_matches_query(recipe: IndexedRecipe, query_words: list[str]) -> bool:
    """A loose "does this recipe look like what the user typed" check
    (e.g. 'lasagne', 'gehaktbal') against title/keywords/cuisine - the same
    freeform fields a recipe's own site would use, unlike dish_type which
    is too coarse-grained for a specific dish name. All words must appear
    (as a substring, so Dutch compounds/plurals still match) - AND rather
    than OR, so a two-word query like 'kip curry' doesn't match every
    recipe that merely contains chicken."""
    return all(word in recipe.search_norm for word in query_words)


def pick_replacement(
    db: Session,
    week_menu: WeekMenu,
    day_of_week: int,
    lang: str = "en",
    query: str | None = None,
    avoid_ids: set[int] | None = None,
) -> tuple[IndexedRecipe | None, str | None]:
    """Picks (without saving) a different recipe of the same course for one
    day. Without `query`, picks randomly, preferring a dish type that
    differs from the neighbouring days. With `query` (e.g. 'lasagne'),
    narrows the candidates to recipes whose title/keywords/cuisine match -
    a deliberate, specific request, so unlike the random path it also
    ignores the recent-use cooldown. `avoid_ids` are recipes to leave out on
    top of those already in use this week (used when pre-picking spare
    candidates for several days at once). Returns (recipe or None, warning)."""
    index = get_index(db)
    day_row = next(d for d in week_menu.days if d.day_of_week == day_of_week)
    current = index.by_id.get(day_row.recipe_id) if day_row.recipe_id else None
    target_course = current.course if current else "hoofdgerecht"

    same_course = [r for r in available_recipes(db) if r.course == target_course]

    query_words = [w for w in normalize_text(query).split() if w] if query else []
    if query_words:
        same_course = [r for r in same_course if _recipe_matches_query(r, query_words)]
        if not same_course:
            return None, t("no_recipe_matches_query", lang, query=query.strip())
    elif not same_course:
        return None, t("no_other_recipes_for_course", lang, course=target_course)

    preferred_ids = preferred_recipe_ids(db)
    recent_ids = set() if query_words else _recently_used_recipe_ids(db, week_menu.week_start_date)

    used_recipe_ids = {d.recipe_id for d in week_menu.days if d.recipe_id}
    used_recipe_ids.discard(day_row.recipe_id)
    used_recipe_ids |= avoid_ids or set()

    neighbour_types = set()
    for neighbour_index in (day_of_week - 1, day_of_week + 1):
        neighbour = next((d for d in week_menu.days if d.day_of_week == neighbour_index), None)
        if neighbour and neighbour.recipe_id and neighbour.recipe_id in index.by_id:
            neighbour_types.add(index.by_id[neighbour.recipe_id].dish_type)

    # Same eligibility rule as the main generator: not used elsewhere this
    # week, and either outside the recent-use cooldown or liked.
    eligible = [
        r
        for r in same_course
        if r.id not in used_recipe_ids and (r.id not in recent_ids or r.rating == "like")
    ]
    best = [r for r in eligible if r.dish_type not in neighbour_types]

    if best:
        return _pick_preferred(best, preferred_ids), None
    if eligible:
        return _pick_preferred(eligible, preferred_ids), None
    candidates = [r for r in same_course if r.id != day_row.recipe_id and r.id not in (avoid_ids or set())]
    if not candidates:
        candidates = [r for r in same_course if r.id != day_row.recipe_id] or same_course
    return _pick_preferred(candidates, preferred_ids), t("repetition_unavoidable", lang)


def set_day_recipe(db: Session, day_row: WeekMenuDay, recipe_id: int) -> WeekMenuDay:
    """Puts a specific recipe on a day. The day's flags describe the old
    dish, so they reset."""
    day_row.recipe_id = recipe_id
    day_row.avg_json = None
    day_row.pinned = False
    day_row.cooked = False
    day_row.skip_shopping = False
    db.commit()
    db.refresh(day_row)
    return day_row


def set_day_avg(db: Session, day_row: WeekMenuDay, choice: dict) -> WeekMenuDay:
    """Makes a day a simple AVG meal. Turning a recipe day into one drops the
    recipe and resets the flags (they described the old dish); changing the
    choices of a day that already is an AVG meal keeps its flags."""
    if day_row.recipe_id:
        day_row.recipe_id = None
        day_row.pinned = False
        day_row.cooked = False
        day_row.skip_shopping = False
    day_row.avg_json = json.dumps(choice)
    db.commit()
    db.refresh(day_row)
    return day_row


def refresh_day(
    db: Session, week_menu: WeekMenu, day_of_week: int, lang: str = "en", query: str | None = None
) -> tuple[WeekMenuDay, str | None]:
    """Swap the recipe on one day for a different pick of the same course."""
    day_row = next(d for d in week_menu.days if d.day_of_week == day_of_week)
    chosen, warning = pick_replacement(db, week_menu, day_of_week, lang, query)
    if chosen is None:
        return day_row, warning
    return set_day_recipe(db, day_row, chosen.id), warning
