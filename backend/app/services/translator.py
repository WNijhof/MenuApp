"""Translates recipe ingredient lines into the active UI language via the
free MyMemory translation API, so a Dutch recipe's ingredients show up in
English (and vice versa) on the shopping list, regardless of which
language the recipe itself is in. This is deliberately separate from the
static app-string dictionary (see i18n.py): ingredient lines are free-form
text scraped from the source site, not a fixed set of keys, so they need
an actual translation call rather than a lookup.

Results are cached in the database (source_text, source_lang, target_lang)
so the same line is only ever sent to the API once. A failed or
rate-limited call falls back to the original text rather than breaking
shopping list generation, and is deliberately NOT cached, so a transient
failure gets retried on the next request instead of being stuck
untranslated forever.
"""

import concurrent.futures
import logging

import requests
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import TranslationCache

logger = logging.getLogger("menuapp.translator")

_API_URL = "https://api.mymemory.translated.net/get"
_REQUEST_TIMEOUT_SECONDS = 8
_MAX_WORKERS = 5

_session = requests.Session()


def _call_api(text: str, source_lang: str, target_lang: str) -> str | None:
    try:
        resp = _session.get(
            _API_URL,
            params={"q": text, "langpair": f"{source_lang}|{target_lang}"},
            timeout=_REQUEST_TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
        data = resp.json()
    except (requests.RequestException, ValueError):
        return None

    if data.get("responseStatus") not in (200, "200"):
        return None
    translated = (data.get("responseData") or {}).get("translatedText")
    # MyMemory returns HTTP 200 with a "MYMEMORY WARNING..." string in the
    # translation field itself (e.g. daily quota exceeded) rather than an
    # error status - treat that the same as a hard failure.
    if not translated or "MYMEMORY WARNING" in translated.upper():
        return None
    return translated


def _get_cached(db: Session, text: str, source_lang: str, target_lang: str) -> str | None:
    row = (
        db.query(TranslationCache)
        .filter_by(source_text=text, source_lang=source_lang, target_lang=target_lang)
        .first()
    )
    return row.translated_text if row else None


def _store(db: Session, text: str, source_lang: str, target_lang: str, translated: str) -> None:
    db.add(
        TranslationCache(
            source_text=text,
            source_lang=source_lang,
            target_lang=target_lang,
            translated_text=translated,
        )
    )
    try:
        db.commit()
    except IntegrityError:
        # Another request cached this exact line concurrently - fine, the
        # value we just translated is used for this response regardless.
        db.rollback()


def translate_lines(
    db: Session, lines: list[str], source_lang: str, target_lang: str
) -> dict[str, str]:
    """Translates a batch of lines, all assumed to be in `source_lang`,
    into `target_lang`. Returns a dict mapping each input line to its
    translated text; a line that fails to translate maps to itself.
    Uncached lines are fetched concurrently (a shopping list can easily
    have a few dozen distinct lines needing translation on first view) -
    only the network calls run in the thread pool, all DB access stays on
    the calling thread/session."""
    if source_lang == target_lang:
        return {line: line for line in lines}

    unique_lines = list(dict.fromkeys(lines))
    result: dict[str, str] = {}
    to_fetch = []
    for line in unique_lines:
        cached = _get_cached(db, line, source_lang, target_lang)
        if cached is not None:
            result[line] = cached
        else:
            to_fetch.append(line)

    if to_fetch:
        with concurrent.futures.ThreadPoolExecutor(max_workers=_MAX_WORKERS) as pool:
            translations = list(
                pool.map(lambda line: _call_api(line, source_lang, target_lang), to_fetch)
            )
        for line, translated in zip(to_fetch, translations):
            if translated:
                result[line] = translated
                _store(db, line, source_lang, target_lang, translated)
            else:
                logger.warning("Translation failed, keeping original text: %r", line)
                result[line] = line

    return result
