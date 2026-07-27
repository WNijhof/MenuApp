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


def get_language(db: Session) -> str:
    """Single household-wide language setting (like the color/course-count
    preferences) - read directly from the settings row rather than threaded
    through request headers, since this is a self-hosted single-tenant app."""
    return get_or_create_settings(db).language
