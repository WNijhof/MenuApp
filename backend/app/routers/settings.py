from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import schemas
from app.database import get_db
from app.services.menu_generator import DAYS_PER_WEEK
from app.services.settings import get_or_create_settings

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("", response_model=schemas.AppSettingsOut)
def get_settings(db: Session = Depends(get_db)):
    return get_or_create_settings(db)


@router.put("", response_model=schemas.AppSettingsOut)
def update_settings(payload: schemas.AppSettingsUpdate, db: Session = Depends(get_db)):
    if any(v < 0 for v in payload.model_dump().values()):
        raise HTTPException(400, "Aantal gerechten kan niet negatief zijn")
    total = payload.default_hoofdgerecht + payload.default_voorgerecht + payload.default_nagerecht
    if total > DAYS_PER_WEEK:
        raise HTTPException(
            400, f"Aantal gerechten kan niet meer dan {DAYS_PER_WEEK} zijn, kreeg {total}"
        )

    settings = get_or_create_settings(db)
    settings.default_hoofdgerecht = payload.default_hoofdgerecht
    settings.default_voorgerecht = payload.default_voorgerecht
    settings.default_nagerecht = payload.default_nagerecht
    db.commit()
    db.refresh(settings)
    return settings
