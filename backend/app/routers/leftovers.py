from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import schemas
from app.database import get_db
from app.i18n import t
from app.models import Leftover
from app.services.settings import get_language

router = APIRouter(prefix="/api/leftovers", tags=["leftovers"])


@router.get("", response_model=list[schemas.LeftoverOut])
def list_leftovers(db: Session = Depends(get_db)):
    return db.query(Leftover).order_by(Leftover.term).all()


@router.post("", response_model=schemas.LeftoverOut)
def create_leftover(payload: schemas.LeftoverCreate, db: Session = Depends(get_db)):
    lang = get_language(db)
    term = payload.term.strip().lower()
    if not term:
        raise HTTPException(400, t("empty_term", lang))
    leftover = Leftover(term=term)
    db.add(leftover)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, t("leftover_exists", lang))
    db.refresh(leftover)
    return leftover


@router.delete("/{leftover_id}")
def delete_leftover(leftover_id: int, db: Session = Depends(get_db)):
    leftover = db.get(Leftover, leftover_id)
    if not leftover:
        raise HTTPException(404, t("leftover_not_found", get_language(db)))
    db.delete(leftover)
    db.commit()
    return {"ok": True}
