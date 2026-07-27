import datetime
import logging

from apscheduler.schedulers.background import BackgroundScheduler

from app.database import SessionLocal
from app.models import Source
from app.services.scraper import sync_source

logger = logging.getLogger("menuapp.scheduler")

scheduler = BackgroundScheduler(timezone="Europe/Amsterdam")


def sync_all_enabled_sources_job():
    db = SessionLocal()
    try:
        sources = db.query(Source).filter(Source.enabled.is_(True)).all()
        for source in sources:
            try:
                pages_checked, recipes_new, recipes_updated, error = sync_source(db, source)
                source.last_synced_at = datetime.datetime.utcnow()
                source.last_sync_found = recipes_new
                source.last_sync_error = error
                db.commit()
                logger.info(
                    "Synced %s: %s pages checked, %s new recipes, %s updated",
                    source.name,
                    pages_checked,
                    recipes_new,
                    recipes_updated,
                )
            except Exception:
                db.rollback()
                logger.exception("Sync failed for source %s", source.name)
    finally:
        db.close()


def start_scheduler():
    if not scheduler.running:
        scheduler.add_job(
            sync_all_enabled_sources_job,
            "cron",
            hour=3,
            minute=0,
            id="daily_sync",
            replace_existing=True,
        )
        scheduler.start()
