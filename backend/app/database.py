from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import DATABASE_URL

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False, "timeout": 30}
)


@event.listens_for(engine, "connect")
def _set_sqlite_pragmas(dbapi_connection, connection_record):
    """WAL mode + a generous busy timeout: multiple sources now sync
    concurrently (each in its own session/thread, see
    services/scraper.py:sync_source_by_id), so more than one writer can be
    committing around the same time. SQLite still only allows one writer
    at a time either way, but WAL lets readers (e.g. someone browsing the
    UI) proceed without waiting on that writer, and the busy timeout gives
    a queued writer time to retry instead of immediately raising "database
    is locked"."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=30000")
    cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
