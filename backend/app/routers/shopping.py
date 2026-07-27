from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import schemas
from app.database import get_db
from app.i18n import t
from app.models import FrequentItem, ShoppingListExtra
from app.services.settings import get_language

router = APIRouter(prefix="/api/shopping", tags=["shopping"])


@router.post("/extras", response_model=schemas.ShoppingListItemOut)
def add_shopping_list_extra(payload: schemas.ShoppingListExtraCreate, db: Session = Depends(get_db)):
    text = payload.text.strip()
    if not text:
        raise HTTPException(400, t("empty_text", get_language(db)))

    extra = ShoppingListExtra(text=text)
    db.add(extra)

    # Also used by the "quick add a favorite" flow (same endpoint, exact
    # favorite text) - remembering/bumping it here is what makes frequent
    # items float to the top of the quick-add list over time.
    frequent = db.query(FrequentItem).filter(FrequentItem.term == text).first()
    if frequent:
        frequent.use_count += 1
    else:
        db.add(FrequentItem(term=text))

    db.commit()
    db.refresh(extra)
    return schemas.ShoppingListItemOut(text=extra.text, extra_id=extra.id)


@router.delete("/extras/{extra_id}")
def delete_shopping_list_extra(extra_id: int, db: Session = Depends(get_db)):
    extra = db.get(ShoppingListExtra, extra_id)
    if not extra:
        raise HTTPException(404, t("item_not_found", get_language(db)))
    db.delete(extra)
    db.commit()
    return {"ok": True}


@router.get("/frequent", response_model=list[schemas.FrequentItemOut])
def list_frequent_items(db: Session = Depends(get_db)):
    return (
        db.query(FrequentItem)
        .order_by(FrequentItem.use_count.desc(), FrequentItem.term)
        .all()
    )


@router.delete("/frequent/{item_id}")
def delete_frequent_item(item_id: int, db: Session = Depends(get_db)):
    item = db.get(FrequentItem, item_id)
    if not item:
        raise HTTPException(404, t("item_not_found", get_language(db)))
    db.delete(item)
    db.commit()
    return {"ok": True}
