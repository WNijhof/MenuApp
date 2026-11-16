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

Being a good network citizen matters here: the backfill can involve
thousands of downloads, and an unthrottled run once flooded the local DNS
resolver (Pi-hole rate-limited the whole host). Therefore:

* one shared requests.Session (keep-alive, so few DNS lookups/handshakes);
* a minimum delay between two downloads from the same host;
* a circuit breaker: repeated network errors pause *all* workers, with a
  growing pause, instead of burning through the queue;
* transient errors (DNS, timeouts, 429/5xx) are retried a few times and never
  recorded as permanent failures;
* permanent failures (403/404, corrupt image, ...) are remembered on disk, so
  a restart does not retry thousands of known-bad images every time.
"""

import io
import json
import logging
import queue
import threading
import time
from pathlib import Path
from urllib.parse import urlparse

import requests
import urllib3
from PIL import Image, ImageOps
from sqlalchemy import event

from app.config import (
    REQUEST_DELAY_SECONDS,
    REQUEST_TIMEOUT_SECONDS,
    THUMBNAIL_DIR,
    THUMBNAIL_MAX_SIZE,
    USER_AGENT,
)
from app.models import Recipe

log = logging.getLogger(__name__)

MAX_DOWNLOAD_BYTES = 8 * 1024 * 1024

# Some image hosts refuse server-side downloads (403). Those recipes simply
# keep using their original image (see routers/recipes.py: /thumb redirects).
_IMAGE_HEADERS = {"User-Agent": USER_AGENT, "Accept": "image/webp,image/*,*/*;q=0.8"}
WORKERS = 2

# Minimum gap between two downloads from the same host.
HOST_DELAY_SECONDS = max(REQUEST_DELAY_SECONDS, 0.75)
# Transient failures are retried this many times per process run, then skipped
# until the next restart.
MAX_ATTEMPTS = 3
# Circuit breaker: after this many consecutive network errors, pause all
# workers; the pause doubles per trip up to the maximum.
BREAKER_THRESHOLD = 5
BREAKER_BASE_PAUSE_SECONDS = 300
BREAKER_MAX_PAUSE_SECONDS = 1800
# Permanent failures are retried after this long (or when the image URL changes).
FAILED_RETRY_SECONDS = 7 * 24 * 3600
_FAILED_SAVE_EVERY = 25

_TRANSIENT_ERRORS = (
    requests.ConnectionError,  # includes DNS failures (EAI_AGAIN) and SSL errors
    requests.Timeout,
    urllib3.exceptions.HTTPError,  # connection dropped mid-download
)
_TRANSIENT_STATUSES = {408, 425, 429, 500, 502, 503, 504}

_session = requests.Session()
_session.headers.update(_IMAGE_HEADERS)

_queue: "queue.Queue[tuple[int, str, int]]" = queue.Queue()
_queued: set[int] = set()
_deferred: set[int] = set()  # transient failures given up on until a restart
_failed: dict[int, tuple[str, float]] = {}  # recipe id -> (image url, failed at)
_queued_lock = threading.Lock()  # guards _queued, _deferred, _failed
_started = False

_host_lock = threading.Lock()
_host_next: dict[str, float] = {}  # host -> monotonic time of next allowed download

_breaker_lock = threading.Lock()
_pause_until = 0.0
_consecutive_net_errors = 0
_pause_level = 0

_save_lock = threading.Lock()
_unsaved_failures = 0
_generated = 0


class _TransientError(Exception):
    """Network-level problem; says nothing about the image itself."""


def thumbnail_path(recipe_id: int) -> Path:
    return Path(THUMBNAIL_DIR) / f"{recipe_id}.webp"


def has_thumbnail(recipe_id: int) -> bool:
    return thumbnail_path(recipe_id).is_file()


def _failed_path() -> Path:
    return Path(THUMBNAIL_DIR) / "failed.json"


def _load_failed() -> None:
    try:
        raw = json.loads(_failed_path().read_text(encoding="utf-8"))
        loaded = {int(k): (str(v["url"]), float(v["ts"])) for k, v in raw.items()}
    except FileNotFoundError:
        return
    except Exception as exc:  # a corrupt file just means we retry once
        log.warning("could not read %s: %s", _failed_path(), exc)
        return
    with _queued_lock:
        _failed.update(loaded)


def _save_failed(force: bool = False) -> None:
    global _unsaved_failures
    with _save_lock:
        if not force and _unsaved_failures < _FAILED_SAVE_EVERY and not _queue.empty():
            return
        if _unsaved_failures == 0 and not force:
            return
        with _queued_lock:
            snapshot = {str(k): {"url": u, "ts": ts} for k, (u, ts) in _failed.items()}
        try:
            path = _failed_path()
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps(snapshot), encoding="utf-8")
            tmp.replace(path)
            _unsaved_failures = 0
        except OSError as exc:
            log.warning("could not write %s: %s", _failed_path(), exc)


def _record_permanent_failure(recipe_id: int, image_url: str) -> None:
    global _unsaved_failures
    with _queued_lock:
        _failed[recipe_id] = (image_url, time.time())
    _unsaved_failures += 1
    _save_failed()


def _is_known_failure(recipe_id: int, image_url: str) -> bool:
    entry = _failed.get(recipe_id)
    if entry is None:
        return False
    url, failed_at = entry
    return url == image_url and time.time() - failed_at < FAILED_RETRY_SECONDS


def enqueue(recipe_id: int, image_url: str | None) -> None:
    """Queue a thumbnail for generation unless it exists, is already queued or
    is known to fail. Cheap enough to call from request handlers."""
    if not image_url or not image_url.startswith(("http://", "https://")):
        return
    if has_thumbnail(recipe_id):
        return
    with _queued_lock:
        if recipe_id in _queued or recipe_id in _deferred:
            return
        if _is_known_failure(recipe_id, image_url):
            return
        _queued.add(recipe_id)
    _queue.put((recipe_id, image_url, 0))


def _wait_if_paused() -> None:
    while True:
        with _breaker_lock:
            remaining = _pause_until - time.monotonic()
        if remaining <= 0:
            return
        time.sleep(min(remaining, 30))


def _wait_for_host(host: str) -> None:
    """Reserve the next download slot for this host and sleep until it."""
    with _host_lock:
        now = time.monotonic()
        start = max(now, _host_next.get(host, 0.0))
        _host_next[host] = start + HOST_DELAY_SECONDS
    if start > now:
        time.sleep(start - now)


def _record_success() -> None:
    global _consecutive_net_errors, _pause_level, _generated
    with _breaker_lock:
        _consecutive_net_errors = 0
        _pause_level = 0
        _generated += 1
        count = _generated
    if count % 250 == 0:
        log.info("thumbnails: %d generated this run, %d queued", count, _queue.qsize())


def _record_network_error(exc: Exception) -> None:
    global _consecutive_net_errors, _pause_level, _pause_until
    with _breaker_lock:
        _consecutive_net_errors += 1
        if _consecutive_net_errors < BREAKER_THRESHOLD:
            return
        _consecutive_net_errors = 0
        _pause_level += 1
        pause = min(BREAKER_BASE_PAUSE_SECONDS * 2 ** (_pause_level - 1), BREAKER_MAX_PAUSE_SECONDS)
        _pause_until = time.monotonic() + pause
    log.warning(
        "thumbnails: %d network errors in a row (last: %s); pausing all thumbnail downloads for %ds",
        BREAKER_THRESHOLD,
        exc,
        pause,
    )


def _generate(recipe_id: int, image_url: str) -> None:
    try:
        with _session.get(image_url, timeout=REQUEST_TIMEOUT_SECONDS, stream=True) as response:
            if response.status_code in _TRANSIENT_STATUSES:
                raise _TransientError(f"HTTP {response.status_code}")
            response.raise_for_status()  # other 4xx/5xx: permanent
            data = response.raw.read(MAX_DOWNLOAD_BYTES + 1, decode_content=True)
    except _TRANSIENT_ERRORS as exc:
        raise _TransientError(str(exc)) from exc
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
        recipe_id, image_url, attempts = _queue.get()
        requeue = False
        try:
            _wait_if_paused()
            _wait_for_host(urlparse(image_url).netloc)
            _generate(recipe_id, image_url)
            _record_success()
            with _queued_lock:
                _failed.pop(recipe_id, None)
        except _TransientError as exc:
            _record_network_error(exc)
            if attempts + 1 < MAX_ATTEMPTS:
                requeue = True
                _queue.put((recipe_id, image_url, attempts + 1))
            else:
                with _queued_lock:
                    _deferred.add(recipe_id)
                log.debug("thumbnail for recipe %s deferred until restart: %s", recipe_id, exc)
        except Exception as exc:  # a bad image must never kill the worker
            _record_permanent_failure(recipe_id, image_url)
            log.debug("thumbnail for recipe %s failed: %s", recipe_id, exc)
        finally:
            if not requeue:
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

    _load_failed()

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
