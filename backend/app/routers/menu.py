import datetime
import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import schemas
from app.database import get_db
from app.models import Offer, WeekMenu, WeekMenuDay
from app.services.categorizer import normalize_offer_terms, recipe_matches_offers
from app.services.menu_generator import DAYS_PER_WEEK, generate_week_menu, refresh_day
from app.services.settings import default_course_counts
from app.services.shopping_list import build_shopping_list

router = APIRouter(prefix="/api/menu", tags=["menu"])


def _week_start_for(day: datetime.date) -> datetime.date:
    """Monday of the week containing `day` - any date the user picks
    snaps to its week's start, so week_start_date stays consistent
    regardless of which day of that week was actually selected."""
    return day - datetime.timedelta(days=day.weekday())


def _current_week_start() -> datetime.date:
    return _week_start_for(datetime.date.today())


def _resolve_week_start(week_start_date: datetime.date | None) -> datetime.date:
    return _week_start_for(week_start_date) if week_start_date else _current_week_start()


def _current_offer_terms(db: Session) -> list[str]:
    return normalize_offer_terms([row.name for row in db.query(Offer).all()])


def _recipe_out_with_offer(recipe, offer_terms: list[str]) -> schemas.RecipeOut:
    has_offer = bool(offer_terms) and recipe_matches_offers(
        json.loads(recipe.ingredients_json or "[]"), offer_terms
    )
    return schemas.RecipeOut.from_model(recipe, has_offer=has_offer)


def _to_week_menu_out(
    week_menu: WeekMenu, warnings: list[str] | None = None, offer_terms: list[str] | None = None
) -> schemas.WeekMenuOut:
    offer_terms = offer_terms or []
    days = []
    for day in sorted(week_menu.days, key=lambda d: d.day_of_week):
        days.append(
            schemas.WeekMenuDayOut(
                day_of_week=day.day_of_week,
                recipe=_recipe_out_with_offer(day.recipe, offer_terms) if day.recipe else None,
            )
        )
    return schemas.WeekMenuOut(
        week_start_date=week_menu.week_start_date,
        days=days,
        course_counts=json.loads(week_menu.course_counts_json or "{}"),
        warnings=warnings or [],
    )


def _validate_course_counts(course_counts: dict[str, int] | None):
    """Fewer than 7 dishes is fine (the remaining days are simply left
    open); more than 7 doesn't fit the week's 7 day-slots."""
    if course_counts is None:
        return
    if any(v < 0 for v in course_counts.values()):
        raise HTTPException(400, "Aantal gerechten kan niet negatief zijn")
    total = sum(course_counts.values())
    if total > DAYS_PER_WEEK:
        raise HTTPException(
            400, f"Aantal gerechten kan niet meer dan {DAYS_PER_WEEK} zijn, kreeg {total}"
        )


def _ephemeral_week_menu(week_start: datetime.date) -> WeekMenu:
    """An in-memory-only stand-in for a week that hasn't been generated
    yet, used so *browsing* to a week (via the week-picker) doesn't
    permanently create and persist a menu for it. Never added to the
    session - nothing here is ever written to the database."""
    week_menu = WeekMenu(week_start_date=week_start, course_counts_json="{}")
    week_menu.days = [WeekMenuDay(day_of_week=i, recipe=None) for i in range(DAYS_PER_WEEK)]
    return week_menu


def _get_or_generate_week_menu(
    db: Session, week_start: datetime.date, persist: bool = True
) -> tuple[WeekMenu, list[str]]:
    week_menu = (
        db.query(WeekMenu).filter(WeekMenu.week_start_date == week_start).first()
    )
    if week_menu:
        return week_menu, []

    if not persist and week_start != _current_week_start():
        # Just looking, not the current week, and nothing generated for it
        # yet - don't create a row merely because it was viewed. It only
        # becomes real once the user explicitly generates it (or acts on
        # it, e.g. a day-reroll).
        return _ephemeral_week_menu(week_start), [
            "Nog geen weekmenu voor deze week — klik op 'Genereer nieuwe week' om er een te maken."
        ]

    # Leftovers are "what's in the fridge right now" - only clear them when
    # generating the *actual* current week, not some other week the user
    # is browsing/planning ahead or looking back at.
    week_menu = generate_week_menu(
        db, week_start, default_course_counts(db), clear_leftovers=week_start == _current_week_start()
    )
    return week_menu, getattr(week_menu, "warnings", [])


@router.get("/current", response_model=schemas.WeekMenuOut)
def get_current_menu(week_start_date: datetime.date | None = None, db: Session = Depends(get_db)):
    week_start = _resolve_week_start(week_start_date)
    week_menu, warnings = _get_or_generate_week_menu(db, week_start, persist=False)
    return _to_week_menu_out(week_menu, warnings, _current_offer_terms(db))


@router.get("/current/shopping-list", response_model=schemas.ShoppingListOut)
def get_current_shopping_list(week_start_date: datetime.date | None = None, db: Session = Depends(get_db)):
    week_start = _resolve_week_start(week_start_date)
    week_menu, _ = _get_or_generate_week_menu(db, week_start, persist=False)
    return schemas.ShoppingListOut(
        week_start_date=week_menu.week_start_date, items=build_shopping_list(db, week_menu)
    )


@router.post("/generate", response_model=schemas.WeekMenuOut)
def generate_menu(
    payload: schemas.GenerateMenuRequest | None = None, db: Session = Depends(get_db)
):
    course_counts = payload.course_counts if payload else None
    _validate_course_counts(course_counts)
    week_start = _resolve_week_start(payload.week_start_date if payload else None)
    week_menu = generate_week_menu(
        db,
        week_start,
        course_counts or default_course_counts(db),
        clear_leftovers=week_start == _current_week_start(),
    )
    return _to_week_menu_out(week_menu, getattr(week_menu, "warnings", []), _current_offer_terms(db))


@router.get("/history", response_model=list[schemas.WeekMenuOut])
def get_menu_history(db: Session = Depends(get_db)):
    week_menus = db.query(WeekMenu).order_by(WeekMenu.week_start_date.desc()).all()
    offer_terms = _current_offer_terms(db)
    return [_to_week_menu_out(w, offer_terms=offer_terms) for w in week_menus]


@router.post("/day/{day_of_week}/refresh", response_model=schemas.WeekMenuDayOut)
def refresh_menu_day(
    day_of_week: int, week_start_date: datetime.date | None = None, db: Session = Depends(get_db)
):
    if day_of_week < 0 or day_of_week > 6:
        raise HTTPException(400, "day_of_week moet tussen 0 en 6 liggen")

    week_start = _resolve_week_start(week_start_date)
    week_menu, _ = _get_or_generate_week_menu(db, week_start)

    day_row, warning = refresh_day(db, week_menu, day_of_week)
    offer_terms = _current_offer_terms(db)
    result = schemas.WeekMenuDayOut(
        day_of_week=day_row.day_of_week,
        recipe=_recipe_out_with_offer(day_row.recipe, offer_terms) if day_row.recipe else None,
        warning=warning,
    )
    return result


@router.delete("/{week_start_date}")
def delete_week_menu(week_start_date: datetime.date, db: Session = Depends(get_db)):
    week_menu = (
        db.query(WeekMenu).filter(WeekMenu.week_start_date == week_start_date).first()
    )
    if not week_menu:
        raise HTTPException(404, "Weekmenu niet gevonden")
    db.delete(week_menu)
    db.commit()
    return {"ok": True}
