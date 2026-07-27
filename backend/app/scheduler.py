import concurrent.futures
import logging

from apscheduler.schedulers.background import BackgroundScheduler

from app.config import MAX_CONCURRENT_SOURCE_SYNCS
from app.database import SessionLocal
from app.models import Source
from app.services.scraper import sync_source_by_id

logger = logging.getLogger("menuapp.scheduler")

scheduler = BackgroundScheduler(timezone="Europe/Amsterdam")


def sync_all_enabled_sources_job():
    db = SessionLocal()
    try:
        source_ids = [
            row.id for row in db.query(Source.id).filter(Source.enabled.is_(True)).all()
        ]
    finally:
        db.close()

    # Same reasoning as routers/sources.py:sync_all_sources - different
    # sources are different sites, so syncing several concurrently doesn't
    # make any single one less polite, it just avoids queueing behind each
    # other. sync_source_by_id opens its own DB session per source, which
    # is required for thread-safety (also handles per-source errors, so a
    # failure here can't sink the rest of the nightly run).
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_CONCURRENT_SOURCE_SYNCS) as pool:
        for result in pool.map(sync_source_by_id, source_ids):
            if result:
                logger.info(
                    "Synced %s: %s pages checked, %s new recipes, %s updated",
                    result["source_name"],
                    result["pages_checked"],
                    result["recipes_new"],
                    result["recipes_updated"],
                )


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
