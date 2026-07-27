from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import schemas
from app.database import get_db
from app.i18n import t
from app.models import ExclusionRule
from app.services.categorizer import expand_exclusion_term, taxonomy_categories
from app.services.settings import get_language

router = APIRouter(prefix="/api/exclusions", tags=["exclusions"])


@router.get("", response_model=list[schemas.ExclusionOut])
def list_exclusions(db: Session = Depends(get_db)):
    rules = db.query(ExclusionRule).order_by(ExclusionRule.term).all()
    return [
        schemas.ExclusionOut(
            id=r.id, term=r.term, expands_to=expand_exclusion_term(r.term)
        )
        for r in rules
    ]


@router.get("/taxonomy", response_model=list[str])
def list_taxonomy_categories():
    return taxonomy_categories()


@router.post("", response_model=schemas.ExclusionOut)
def create_exclusion(payload: schemas.ExclusionCreate, db: Session = Depends(get_db)):
    lang = get_language(db)
    term = payload.term.strip().lower()
    if not term:
        raise HTTPException(400, t("empty_term", lang))
    rule = ExclusionRule(term=term)
    db.add(rule)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, t("exclusion_exists", lang))
    db.refresh(rule)
    return schemas.ExclusionOut(
        id=rule.id, term=rule.term, expands_to=expand_exclusion_term(rule.term)
    )


@router.delete("/{exclusion_id}")
def delete_exclusion(exclusion_id: int, db: Session = Depends(get_db)):
    rule = db.get(ExclusionRule, exclusion_id)
    if not rule:
        raise HTTPException(404, t("exclusion_not_found", get_language(db)))
    db.delete(rule)
    db.commit()
    return {"ok": True}
