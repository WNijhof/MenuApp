import os

DATABASE_PATH = os.environ.get("DATABASE_PATH", "./menuapp.db")
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

# Polite scraping defaults - keep low to avoid hammering third-party sites.
# This governs the pace *within* one source's crawl only - it does not
# change when multiple different sources are synced concurrently (see
# MAX_CONCURRENT_SOURCE_SYNCS), since that doesn't add load to any single
# site.
REQUEST_TIMEOUT_SECONDS = 10
REQUEST_DELAY_SECONDS = 0.75
DEFAULT_MAX_PAGES_PER_SYNC = 300
USER_AGENT = "MenuappPersonalRecipeAggregator/1.0 (+self-hosted, single user)"

# How many *different* sources may sync concurrently during "sync all" /
# the nightly job. Safe to raise without becoming impolite to any one
# site - each source is a different domain, paced independently by
# REQUEST_DELAY_SECONDS. Bounded mainly to keep local resource usage (DB
# writer contention, open connections) sane, not out of politeness.
MAX_CONCURRENT_SOURCE_SYNCS = 4

# Recipe pages older than this are re-fetched on a full re-sync.
STALE_AFTER_DAYS = 30
