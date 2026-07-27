from sqlalchemy.orm import Session

from app.models import AppSettings

SETTINGS_ID = 1


def get_or_create_settings(db: Session) -> AppSettings:
    settings = db.get(AppSettings, SETTINGS_ID)
    if not settings:
        settings = AppSettings(id=SETTINGS_ID)
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


def default_course_counts(db: Session) -> dict[str, int]:
    settings = get_or_create_settings(db)
    return {
        "hoofdgerecht": settings.default_hoofdgerecht,
        "voorgerecht": settings.default_voorgerecht,
        "nagerecht": settings.default_nagerecht,
    }
