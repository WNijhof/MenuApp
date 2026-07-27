import re

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import schemas
from app.database import get_db
from app.i18n import t
from app.services.menu_generator import DAYS_PER_WEEK
from app.services.settings import get_or_create_settings

router = APIRouter(prefix="/api/settings", tags=["settings"])

_HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
SUPPORTED_LANGUAGES = {"en", "nl"}


def _validate_hex_color(value: str | None, field_key: str, lang: str):
    if value is not None and not _HEX_COLOR_RE.match(value):
        raise HTTPException(400, t("invalid_hex_color", lang, field=t(field_key, lang)))


@router.get("", response_model=schemas.AppSettingsOut)
def get_settings(db: Session = Depends(get_db)):
    return get_or_create_settings(db)


@router.put("", response_model=schemas.AppSettingsOut)
def update_settings(payload: schemas.AppSettingsUpdate, db: Session = Depends(get_db)):
    # Validate (and speak) in the language the user is switching to, since
    # by the time this request fires the frontend has already applied it.
    lang = payload.language if payload.language in SUPPORTED_LANGUAGES else "en"

    counts = (payload.default_hoofdgerecht, payload.default_voorgerecht, payload.default_nagerecht)
    if any(v < 0 for v in counts):
        raise HTTPException(400, t("course_counts_negative", lang))
    total = sum(counts)
    if total > DAYS_PER_WEEK:
        raise HTTPException(400, t("course_counts_too_high", lang, max=DAYS_PER_WEEK, total=total))
    _validate_hex_color(payload.background_color, "field_background_color", lang)
    _validate_hex_color(payload.accent_color, "field_accent_color", lang)

    settings = get_or_create_settings(db)
    settings.default_hoofdgerecht = payload.default_hoofdgerecht
    settings.default_voorgerecht = payload.default_voorgerecht
    settings.default_nagerecht = payload.default_nagerecht
    settings.background_color = payload.background_color
    settings.accent_color = payload.accent_color
    settings.language = lang
    db.commit()
    db.refresh(settings)
    return settings
