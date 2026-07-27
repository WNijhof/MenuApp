from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import schemas
from app.database import get_db
from app.models import PantryStaple

router = APIRouter(prefix="/api/pantry", tags=["pantry"])


@router.get("", response_model=list[schemas.PantryStapleOut])
def list_pantry_staples(db: Session = Depends(get_db)):
    return db.query(PantryStaple).order_by(PantryStaple.term).all()


@router.post("", response_model=schemas.PantryStapleOut)
def create_pantry_staple(payload: schemas.PantryStapleCreate, db: Session = Depends(get_db)):
    term = payload.term.strip().lower()
    if not term:
        raise HTTPException(400, "Lege term")
    staple = PantryStaple(term=term)
    db.add(staple)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Dit basisproduct staat al in de lijst")
    db.refresh(staple)
    return staple


@router.delete("/{staple_id}")
def delete_pantry_staple(staple_id: int, db: Session = Depends(get_db)):
    staple = db.get(PantryStaple, staple_id)
    if not staple:
        raise HTTPException(404, "Basisproduct niet gevonden")
    db.delete(staple)
    db.commit()
    return {"ok": True}
