from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import schemas
from app.database import get_db
from app.models import Leftover

router = APIRouter(prefix="/api/leftovers", tags=["leftovers"])


@router.get("", response_model=list[schemas.LeftoverOut])
def list_leftovers(db: Session = Depends(get_db)):
    return db.query(Leftover).order_by(Leftover.term).all()


@router.post("", response_model=schemas.LeftoverOut)
def create_leftover(payload: schemas.LeftoverCreate, db: Session = Depends(get_db)):
    term = payload.term.strip().lower()
    if not term:
        raise HTTPException(400, "Lege term")
    leftover = Leftover(term=term)
    db.add(leftover)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Dit restje staat al in de lijst")
    db.refresh(leftover)
    return leftover


@router.delete("/{leftover_id}")
def delete_leftover(leftover_id: int, db: Session = Depends(get_db)):
    leftover = db.get(Leftover, leftover_id)
    if not leftover:
        raise HTTPException(404, "Restje niet gevonden")
    db.delete(leftover)
    db.commit()
    return {"ok": True}
