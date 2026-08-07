import json
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, SessionLocal, engine
from app.models import Recipe, Source
from app.routers import (
    exclusions,
    leftovers,
    menu,
    offers,
    pantry,
    recipes,
    settings,
    shopping,
    sources,
)
from app.scheduler import start_scheduler
from app.services.language_detect import detect_language

SEED_SOURCES_PATH = Path(__file__).resolve().parent / "data" / "seed_sources.json"

# (table, column, DDL type/default) pairs to backfill onto an existing
# sqlite file. create_all() only adds missing *tables*, not missing
# columns on a table that already exists, so new columns need a manual
# ALTER TABLE - no formal migration tool is set up for this project.
_COLUMN_MIGRATIONS = [
    ("recipes", "course", "VARCHAR(20) DEFAULT 'hoofdgerecht'"),
    ("recipes", "rating", "VARCHAR(10)"),
    ("recipes", "rated_at", "DATETIME"),
    # No DEFAULT on purpose - NULL here is what marks a pre-existing recipe
    # as needing the one-time detection backfill below. Every insert going
    # forward (scraper.py, routers/recipes.py) always sets this explicitly.
    ("recipes", "language", "VARCHAR(5)"),
    ("week_menus", "course_counts_json", "TEXT DEFAULT '{}'"),
    ("week_menus", "frozen", "BOOLEAN DEFAULT 0"),
    ("app_settings", "background_color", "VARCHAR(20)"),
    ("app_settings", "accent_color", "VARCHAR(20)"),
    ("app_settings", "language", "VARCHAR(5) DEFAULT 'en'"),
]


def _run_light_migrations():
    with engine.connect() as conn:
        for table, column, ddl in _COLUMN_MIGRATIONS:
            existing_columns = {
                row[1] for row in conn.exec_driver_sql(f"PRAGMA table_info({table})")
            }
            if column not in existing_columns:
                conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")
        conn.commit()


def _backfill_recipe_language():
    """One-time detection pass for recipes scraped before Recipe.language
    existed (see the migration entry above) - runs on every startup but is
    a no-op past the first one, since every write path sets the field
    explicitly from then on. Only heuristic detection is available here
    (no page HTML left to re-read a schema.org `inLanguage` hint from); a
    future re-sync will correct anything this guesses wrong."""
    db = SessionLocal()
    try:
        recipes_to_backfill = db.query(Recipe).filter(Recipe.language.is_(None)).all()
        for recipe in recipes_to_backfill:
            text = " ".join(
                filter(
                    None,
                    [
                        recipe.title,
                        *json.loads(recipe.instructions_json or "[]"),
                        *json.loads(recipe.ingredients_json or "[]"),
                    ],
                )
            )
            recipe.language = detect_language(text)
        db.commit()
    finally:
        db.close()


def _seed_sources_if_empty():
    db = SessionLocal()
    try:
        if db.query(Source).count() > 0:
            return
        with open(SEED_SOURCES_PATH, "r", encoding="utf-8") as f:
            seed_sources = json.load(f)
        for entry in seed_sources:
            db.add(Source(name=entry["name"], base_url=entry["base_url"]))
        db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    _run_light_migrations()
    _backfill_recipe_language()
    _seed_sources_if_empty()
    start_scheduler()
    yield


app = FastAPI(title="Menuapp", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sources.router)
app.include_router(recipes.router)
app.include_router(exclusions.router)
app.include_router(menu.router)
app.include_router(pantry.router)
app.include_router(leftovers.router)
app.include_router(shopping.router)
app.include_router(offers.router)
app.include_router(settings.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
