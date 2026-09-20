"""Small, cached thumbnails for recipe images.

Recipe sites serve full-size photos (often several hundred KB each); a week
view or a scrolling recipe list showing dozens of them is what made the UI
feel sluggish. Each recipe's image is downloaded once in the background,
shrunk to a small WebP (~10 KB) under THUMBNAIL_DIR and served from there
(routers/recipes.py: GET /{id}/thumb) with long-lived cache headers.

Generation never blocks a request: new/changed recipes are queued as they
are saved (SQLAlchemy mapper events), and on startup any recipe still
missing a thumbnail is queued too. Until a thumbnail exists the endpoint
just redirects to the original image.
"""

import io
import logging
import queue
import threading
from pathlib import Path

import requests
from PIL import Image, ImageOps
from sqlalchemy import event

from app.config import REQUEST_TIMEOUT_SECONDS, THUMBNAIL_DIR, THUMBNAIL_MAX_SIZE, USER_AGENT
from app.models import Recipe

log = logging.getLogger(__name__)

MAX_DOWNLOAD_BYTES = 8 * 1024 * 1024

# Some image hosts refuse server-side downloads (403). Those recipes simply
# keep using their original image (see routers/recipes.py: /thumb redirects).
_IMAGE_HEADERS = {"User-Agent": USER_AGENT, "Accept": "image/webp,image/*,*/*;q=0.8"}
WORKERS = 3

_queue: "queue.Queue[tuple[int, str]]" = queue.Queue()
_queued: set[int] = set()
_failed: set[int] = set()  # this process's failures; retried after a restart
_queued_lock = threading.Lock()
_started = False


def thumbnail_path(recipe_id: int) -> Path:
    return Path(THUMBNAIL_DIR) / f"{recipe_id}.webp"


def has_thumbnail(recipe_id: int) -> bool:
    return thumbnail_path(recipe_id).is_file()


def enqueue(recipe_id: int, image_url: str | None) -> None:
    """Queue a thumbnail for generation unless it exists or is already
    queued. Cheap enough to call from request handlers."""
    if not image_url or not image_url.startswith(("http://", "https://")):
        return
    if recipe_id in _failed or has_thumbnail(recipe_id):
        return
    with _queued_lock:
        if recipe_id in _queued:
            return
        _queued.add(recipe_id)
    _queue.put((recipe_id, image_url))


def _generate(recipe_id: int, image_url: str) -> None:
    response = requests.get(
        image_url,
        timeout=REQUEST_TIMEOUT_SECONDS,
        headers=_IMAGE_HEADERS,
        stream=True,
    )
    response.raise_for_status()
    data = response.raw.read(MAX_DOWNLOAD_BYTES + 1, decode_content=True)
    if len(data) > MAX_DOWNLOAD_BYTES:
        raise ValueError("image too large")

    image = Image.open(io.BytesIO(data))
    image = ImageOps.exif_transpose(image)
    image.thumbnail((THUMBNAIL_MAX_SIZE, THUMBNAIL_MAX_SIZE), Image.LANCZOS)
    if image.mode not in ("RGB", "L"):
        image = image.convert("RGB")

    path = thumbnail_path(recipe_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    image.save(tmp, format="WEBP", quality=70, method=4)
    tmp.replace(path)  # atomic: a request never sees a half-written file


def _worker() -> None:
    while True:
        recipe_id, image_url = _queue.get()
        try:
            _generate(recipe_id, image_url)
        except Exception as exc:  # a bad image must never kill the worker
            _failed.add(recipe_id)
            log.debug("thumbnail for recipe %s failed: %s", recipe_id, exc)
        finally:
            with _queued_lock:
                _queued.discard(recipe_id)
            _queue.task_done()


def _on_recipe_saved(mapper, connection, target) -> None:
    enqueue(target.id, target.image_url)


def start() -> None:
    """Start the background workers (idempotent), hook recipe saves, and
    queue every existing recipe that still lacks a thumbnail."""
    global _started
    if _started:
        return
    _started = True

    for i in range(WORKERS):
        threading.Thread(target=_worker, name=f"thumbnail-{i}", daemon=True).start()

    event.listen(Recipe, "after_insert", _on_recipe_saved)
    event.listen(Recipe, "after_update", _on_recipe_saved)

    def backfill() -> None:
        from app.database import SessionLocal

        db = SessionLocal()
        try:
            for recipe_id, image_url in db.query(Recipe.id, Recipe.image_url).filter(
                Recipe.image_url.isnot(None)
            ):
                enqueue(recipe_id, image_url)
        finally:
            db.close()

    threading.Thread(target=backfill, name="thumbnail-backfill", daemon=True).start()
