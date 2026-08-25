import datetime
import json
import uuid

import requests
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import case
from sqlalchemy.orm import Session

from app import schemas
from app.database import get_db
from app.i18n import t
from app.models import Offer, Recipe
from app.services.categorizer import TermMatcher, compile_terms, infer_course, infer_dish_type, normalize_offer_terms
from app.services.language_detect import detect_language
from app.services.scraper import fetch_single_recipe
from app.services.settings import get_language

router = APIRouter(prefix="/api/recipes", tags=["recipes"])

VALID_RATINGS = {"like", "dislike"}
VALID_COURSES = {"voorgerecht", "hoofdgerecht", "nagerecht"}


def _clean_lines(lines: list[str]) -> list[str]:
    return [line.strip() for line in lines if line.strip()]


def _apply_manual_payload(recipe: Recipe, payload: schemas.RecipeManualCreate, lang: str) -> None:
    title = payload.title.strip()
    ingredients = _clean_lines(payload.ingredients)
    instructions = _clean_lines(payload.instructions)
    if not title:
        raise HTTPException(400, t("recipe_title_required", lang))
    if not ingredients:
        raise HTTPException(400, t("recipe_ingredients_required", lang))
    if payload.course is not None and payload.course not in VALID_COURSES:
        raise HTTPException(400, t("invalid_course", lang))

    recipe.title = title
    recipe.ingredients_json = json.dumps(ingredients)
    recipe.instructions_json = json.dumps(instructions)
    recipe.servings = payload.servings.strip() if payload.servings else None
    recipe.dish_type = infer_dish_type(title, None, None, ingredients)
    recipe.course = payload.course or infer_course(title, None, None)
    recipe.language = detect_language(" ".join([title, *ingredients, *instructions]))


def _current_offer_matcher(db: Session) -> TermMatcher:
    """Compiled once per request - see categorizer.compile_terms for why
    that matters when checking hundreds of recipes against hundreds of
    offers (re-deriving the matcher per recipe used to dominate the
    runtime of listing recipes)."""
    return compile_terms(normalize_offer_terms([row.name for row in db.query(Offer).all()]))


def _has_offer(recipe: Recipe, offer_matcher: TermMatcher) -> bool:
    return offer_matcher.matches(json.loads(recipe.ingredients_json or "[]"))


@router.get("", response_model=list[schemas.RecipeOut])
def list_recipes(course: str | None = None, rating: str | None = None, db: Session = Depends(get_db)):
    query = db.query(Recipe)
    if course:
        query = query.filter(Recipe.course == course)
    if rating:
        query = query.filter(Recipe.rating == rating)
    # Favorites (rating == "like") sort first, then alphabetically. A plain
    # `!=` comparison would misorder NULL ratings under SQL's three-valued
    # logic, so use an explicit CASE for an unambiguous 0/1 sort key.
    favorite_first = case((Recipe.rating == "like", 0), else_=1)
    recipes = query.order_by(favorite_first, Recipe.title).all()
    offer_matcher = _current_offer_matcher(db)
    return [schemas.RecipeOut.from_model(r, has_offer=_has_offer(r, offer_matcher)) for r in recipes]


@router.post("/add-url", response_model=schemas.RecipeOut)
def add_recipe_by_url(payload: schemas.AddRecipeUrl, db: Session = Depends(get_db)):
    existing = db.query(Recipe).filter(Recipe.url == payload.url).first()
    if existing:
        return schemas.RecipeOut.from_model(existing, has_offer=_has_offer(existing, _current_offer_matcher(db)))

    lang = get_language(db)
    try:
        parsed = fetch_single_recipe(payload.url)
    except requests.RequestException as exc:
        raise HTTPException(400, t("fetch_page_failed", lang, error=exc))

    if not parsed:
        raise HTTPException(422, t("no_recipe_data_found", lang))

    recipe = Recipe(
        source_id=None,
        url=parsed["url"],
        title=parsed["title"],
        image_url=parsed["image_url"],
        dish_type=parsed["dish_type"],
        course=parsed["course"],
        cuisine=parsed["cuisine"],
        keywords=parsed["keywords"],
        language=parsed["language"],
        ingredients_json=json.dumps(parsed["ingredients"]),
        instructions_json=json.dumps(parsed["instructions"]),
        prep_time_minutes=parsed["prep_time_minutes"],
        cook_time_minutes=parsed["cook_time_minutes"],
        total_time_minutes=parsed["total_time_minutes"],
        servings=parsed["servings"],
    )
    db.add(recipe)
    db.commit()
    db.refresh(recipe)
    return schemas.RecipeOut.from_model(recipe, has_offer=_has_offer(recipe, _current_offer_matcher(db)))


@router.post("/manual", response_model=schemas.RecipeOut)
def add_manual_recipe(payload: schemas.RecipeManualCreate, db: Session = Depends(get_db)):
    lang = get_language(db)
    # No real page behind a hand-typed recipe, so `url` (unique + required,
    # see models.Recipe) gets a synthetic placeholder instead - never
    # rendered as a clickable link by the frontend (is_manual gates that).
    recipe = Recipe(source_id=None, url=f"manual:{uuid.uuid4()}", is_manual=True)
    _apply_manual_payload(recipe, payload, lang)
    db.add(recipe)
    db.commit()
    db.refresh(recipe)
    return schemas.RecipeOut.from_model(recipe, has_offer=_has_offer(recipe, _current_offer_matcher(db)))


@router.patch("/{recipe_id}/manual", response_model=schemas.RecipeOut)
def update_manual_recipe(recipe_id: int, payload: schemas.RecipeManualCreate, db: Session = Depends(get_db)):
    lang = get_language(db)
    recipe = db.get(Recipe, recipe_id)
    if not recipe:
        raise HTTPException(404, t("recipe_not_found", lang))
    if not recipe.is_manual:
        raise HTTPException(400, t("recipe_not_manual", lang))

    _apply_manual_payload(recipe, payload, lang)
    db.commit()
    db.refresh(recipe)
    return schemas.RecipeOut.from_model(recipe, has_offer=_has_offer(recipe, _current_offer_matcher(db)))


@router.patch("/{recipe_id}/rating", response_model=schemas.RecipeOut)
def rate_recipe(recipe_id: int, payload: schemas.RatingUpdate, db: Session = Depends(get_db)):
    recipe = db.get(Recipe, recipe_id)
    if not recipe:
        raise HTTPException(404, t("recipe_not_found", get_language(db)))
    if payload.rating is not None and payload.rating not in VALID_RATINGS:
        raise HTTPException(400, t("invalid_rating", get_language(db)))

    recipe.rating = payload.rating
    recipe.rated_at = datetime.datetime.utcnow() if payload.rating else None
    db.commit()
    db.refresh(recipe)
    return schemas.RecipeOut.from_model(recipe, has_offer=_has_offer(recipe, _current_offer_matcher(db)))


@router.delete("/{recipe_id}")
def delete_recipe(recipe_id: int, db: Session = Depends(get_db)):
    recipe = db.get(Recipe, recipe_id)
    if not recipe:
        raise HTTPException(404, t("recipe_not_found", get_language(db)))
    db.delete(recipe)
    db.commit()
    return {"ok": True}
