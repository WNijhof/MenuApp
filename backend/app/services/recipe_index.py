"""In-memory index of every recipe's lightweight, pre-normalized data.

Swapping a dish used to load every Recipe row (including the big
instructions blob), JSON-parse every ingredient list and re-normalize it -
on every single click. This index does that work once: each recipe's
searchable text, ingredient text and tokens are computed a single time, kept
in memory, and rebuilt only when a recipe actually changes (SQLAlchemy
mapper events below flip the dirty flag on any insert/update/delete).

Derived results that are expensive against a big collection - "which
recipes survive the exclusions", "which use an offer or leftover" - are
cached on top, keyed on the inputs that could change them.
"""

import json
import threading
from dataclasses import dataclass

from sqlalchemy import event, inspect
from sqlalchemy.orm import Session

from app.models import ExclusionRule, Leftover, Offer, Recipe
from app.services.categorizer import (
    TermMatcher,
    _tokenize,
    compile_exclusion_terms,
    compile_terms,
    normalize_offer_terms,
    normalize_terms,
    normalize_text,
)


@dataclass(slots=True)
class IndexedRecipe:
    id: int
    title: str
    title_norm: str
    search_norm: str  # title + keywords + cuisine, normalized
    dish_type: str
    course: str
    rating: str | None
    is_manual: bool
    language: str
    ingredients_text: str  # normalized, " | "-joined
    tokens: frozenset[str]


class RecipeIndex:
    def __init__(self, recipes: list[IndexedRecipe], version: int):
        self.recipes = recipes
        self.by_id = {r.id: r for r in recipes}
        self.version = version


_lock = threading.Lock()
_dirty = True
_version = 0
_index: RecipeIndex | None = None
_derived_cache: dict = {}


def invalidate(*_args, **_kwargs) -> None:
    global _dirty
    _dirty = True


def _on_recipe_updated(mapper, connection, target) -> None:
    """A like/dislike is by far the most frequent edit, and it happens on
    every swipe-style interaction - patch the one indexed entry instead of
    rebuilding the whole index for it."""
    changed = {a.key for a in inspect(target).attrs if a.history.has_changes()}
    if changed and changed <= {"rating", "rated_at"} and _index is not None and not _dirty:
        entry = _index.by_id.get(target.id)
        if entry is not None:
            entry.rating = target.rating
            return
    invalidate()


event.listen(Recipe, "after_insert", invalidate)
event.listen(Recipe, "after_delete", invalidate)
event.listen(Recipe, "after_update", _on_recipe_updated)


def get_index(db: Session) -> RecipeIndex:
    global _dirty, _version, _index
    if _index is not None and not _dirty:
        return _index
    with _lock:
        if _index is not None and not _dirty:
            return _index
        # Clear the flag before reading: a write landing mid-rebuild sets it
        # again and is picked up by the next call.
        _dirty = False
        rows = db.query(
            Recipe.id,
            Recipe.title,
            Recipe.keywords,
            Recipe.cuisine,
            Recipe.dish_type,
            Recipe.course,
            Recipe.rating,
            Recipe.is_manual,
            Recipe.language,
            Recipe.ingredients_json,
        ).all()
        recipes = []
        for r in rows:
            ingredients_text = normalize_text(" | ".join(json.loads(r.ingredients_json or "[]")))
            recipes.append(
                IndexedRecipe(
                    id=r.id,
                    title=r.title,
                    title_norm=normalize_text(r.title),
                    search_norm=normalize_text(" ".join(filter(None, [r.title, r.keywords, r.cuisine]))),
                    dish_type=r.dish_type,
                    course=r.course,
                    rating=r.rating,
                    is_manual=bool(r.is_manual),
                    language=r.language or "nl",
                    ingredients_text=ingredients_text,
                    tokens=frozenset(_tokenize(ingredients_text)),
                )
            )
        _version += 1
        _index = RecipeIndex(recipes, _version)
        _derived_cache.clear()
        return _index


def _cached(key, compute):
    if key not in _derived_cache:
        # Keys embed the index version, so older entries are dead weight
        # once the index is rebuilt - just cap the size.
        if len(_derived_cache) > 32:
            _derived_cache.clear()
        _derived_cache[key] = compute()
    return _derived_cache[key]


def available_recipes(db: Session) -> list[IndexedRecipe]:
    """Index minus disliked recipes and ingredient-exclusion matches. The
    (expensive) exclusion matching is cached per index version; the cheap
    dislike filter runs on top each call, so rating a recipe never forces
    the exclusion scan to be redone."""
    index = get_index(db)
    terms = tuple(sorted(row.term for row in db.query(ExclusionRule.term).all()))

    def compute():
        if not terms:
            return index.recipes
        matcher = compile_exclusion_terms(list(terms))
        return [r for r in index.recipes if not matcher.matches_normalized(r.ingredients_text, r.tokens)]

    allowed = _cached(("allowed", index.version, terms), compute)
    return [r for r in allowed if r.rating != "dislike"]


def preferred_recipe_ids(db: Session) -> set[int]:
    """Ids of recipes using a tracked leftover or an ingredient on offer."""
    index = get_index(db)
    leftover_terms = tuple(sorted(normalize_terms([row.term for row in db.query(Leftover.term).all()])))
    offer_terms = tuple(sorted(set(normalize_offer_terms([row.name for row in db.query(Offer.name).all()]))))
    if not leftover_terms and not offer_terms:
        return set()

    def compute():
        leftover_matcher = compile_terms(list(leftover_terms))
        offer_matcher = compile_terms(list(offer_terms))
        return {
            r.id
            for r in index.recipes
            if leftover_matcher.matches_normalized(r.ingredients_text, r.tokens)
            or offer_matcher.matches_normalized(r.ingredients_text, r.tokens)
        }

    return _cached(("preferred", index.version, leftover_terms, offer_terms), compute)


def current_offer_matcher(db: Session) -> TermMatcher:
    """Compiled offer matcher, rebuilt only when the set of offers changes."""
    names = tuple(sorted(row.name for row in db.query(Offer.name).all()))
    return _cached(("offers", names), lambda: compile_terms(normalize_offer_terms(list(names))))


def search_titles(
    db: Session, query: str, course: str | None = None, limit: int = 8
) -> list[IndexedRecipe]:
    """Type-ahead lookup over recipe titles: every typed word must appear
    in the title (substring, accent-insensitive); titles starting with the
    query come first, then shorter titles."""
    words = [w for w in normalize_text(query).split() if w]
    if not words:
        return []
    joined = " ".join(words)
    hits = [
        r
        for r in available_recipes(db)
        if (course is None or r.course == course) and all(w in r.title_norm for w in words)
    ]
    hits.sort(key=lambda r: (not r.title_norm.startswith(joined), len(r.title_norm), r.title_norm))
    return hits[:limit]
