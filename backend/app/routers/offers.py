from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import schemas
from app.database import get_db
from app.models import Offer
from app.services.offers_scraper import SUPPORTED_STORES, sync_store_offers

router = APIRouter(prefix="/api/offers", tags=["offers"])


@router.get("", response_model=list[schemas.OfferOut])
def list_offers(store: str | None = None, db: Session = Depends(get_db)):
    query = db.query(Offer)
    if store:
        query = query.filter(Offer.store == store)
    return query.order_by(Offer.name).all()


@router.post("/sync", response_model=list[schemas.OfferSyncResult])
def sync_offers(store: str | None = None, db: Session = Depends(get_db)):
    stores = [store] if store else SUPPORTED_STORES
    results = []
    for s in stores:
        if s not in SUPPORTED_STORES:
            raise HTTPException(400, f"Onbekende of niet-ondersteunde winkel: {s}")
        count = sync_store_offers(db, s)
        results.append(schemas.OfferSyncResult(store=s, offers_found=count))
    return results
