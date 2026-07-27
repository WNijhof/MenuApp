from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import schemas
from app.database import get_db
from app.i18n import t
from app.models import PantryStaple
from app.services.settings import get_language

router = APIRouter(prefix="/api/pantry", tags=["pantry"])


@router.get("", response_model=list[schemas.PantryStapleOut])
def list_pantry_staples(db: Session = Depends(get_db)):
    return db.query(PantryStaple).order_by(PantryStaple.term).all()


@router.post("", response_model=schemas.PantryStapleOut)
def create_pantry_staple(payload: schemas.PantryStapleCreate, db: Session = Depends(get_db)):
    lang = get_language(db)
    term = payload.term.strip().lower()
    if not term:
        raise HTTPException(400, t("empty_term", lang))
    staple = PantryStaple(term=term)
    db.add(staple)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, t("pantry_staple_exists", lang))
    db.refresh(staple)
    return staple


@router.delete("/{staple_id}")
def delete_pantry_staple(staple_id: int, db: Session = Depends(get_db)):
    staple = db.get(PantryStaple, staple_id)
    if not staple:
        raise HTTPException(404, t("pantry_staple_not_found", get_language(db)))
    db.delete(staple)
    db.commit()
    return {"ok": True}
