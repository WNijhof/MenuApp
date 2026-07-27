import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app import schemas
from app.database import get_db
from app.models import Recipe, Source
from app.services.scraper import sync_source

router = APIRouter(prefix="/api/sources", tags=["sources"])
logger = logging.getLogger("menuapp.sources")


def _run_sync(db: Session, source: Source) -> tuple[int, int, int, str | None]:
    """Runs sync_source, turning any unexpected exception into an
    error string instead of letting it 500 the request - a single bad
    page/site shouldn't take down the sync button, matching how the
    nightly scheduler already isolates failures per source."""
    try:
        return sync_source(db, source)
    except Exception as exc:  # noqa: BLE001 - surface any sync failure
        db.rollback()
        logger.exception("Sync failed for source %s", source.name)
        return 0, 0, 0, f"Onverwachte fout tijdens synchroniseren: {exc}"


@router.get("", response_model=list[schemas.SourceOut])
def list_sources(db: Session = Depends(get_db)):
    counts = dict(
        db.query(Recipe.source_id, func.count(Recipe.id))
        .group_by(Recipe.source_id)
        .all()
    )
    sources = db.query(Source).order_by(Source.name).all()
    return [
        schemas.SourceOut(
            id=s.id,
            name=s.name,
            base_url=s.base_url,
            sitemap_url=s.sitemap_url,
            enabled=s.enabled,
            max_pages=s.max_pages,
            last_synced_at=s.last_synced_at,
            last_sync_found=s.last_sync_found,
            last_sync_error=s.last_sync_error,
            recipe_count=counts.get(s.id, 0),
        )
        for s in sources
    ]


@router.post("", response_model=schemas.SourceOut)
def create_source(payload: schemas.SourceCreate, db: Session = Depends(get_db)):
    source = Source(**payload.model_dump())
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


@router.patch("/{source_id}", response_model=schemas.SourceOut)
def update_source(source_id: int, payload: schemas.SourceUpdate, db: Session = Depends(get_db)):
    source = db.get(Source, source_id)
    if not source:
        raise HTTPException(404, "Bron niet gevonden")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(source, field, value)
    db.commit()
    db.refresh(source)
    return source


@router.delete("/{source_id}")
def delete_source(source_id: int, db: Session = Depends(get_db)):
    source = db.get(Source, source_id)
    if not source:
        raise HTTPException(404, "Bron niet gevonden")
    db.delete(source)
    db.commit()
    return {"ok": True}


@router.post("/{source_id}/sync", response_model=schemas.SyncResult)
def sync_single_source(source_id: int, db: Session = Depends(get_db)):
    source = db.get(Source, source_id)
    if not source:
        raise HTTPException(404, "Bron niet gevonden")

    import datetime

    pages_checked, recipes_new, recipes_updated, error = _run_sync(db, source)
    source.last_synced_at = datetime.datetime.utcnow()
    source.last_sync_found = recipes_new
    source.last_sync_error = error
    db.commit()

    return schemas.SyncResult(
        source_id=source.id,
        source_name=source.name,
        pages_checked=pages_checked,
        recipes_found=recipes_new,
        recipes_updated=recipes_updated,
        error=error,
    )


@router.post("/sync-all", response_model=list[schemas.SyncResult])
def sync_all_sources(db: Session = Depends(get_db)):
    import datetime

    results = []
    for source in db.query(Source).filter(Source.enabled.is_(True)).all():
        pages_checked, recipes_new, recipes_updated, error = _run_sync(db, source)
        source.last_synced_at = datetime.datetime.utcnow()
        source.last_sync_found = recipes_new
        source.last_sync_error = error
        db.commit()
        results.append(
            schemas.SyncResult(
                source_id=source.id,
                source_name=source.name,
                pages_checked=pages_checked,
                recipes_found=recipes_new,
                recipes_updated=recipes_updated,
                error=error,
            )
        )
    return results
