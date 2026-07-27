import os

DATABASE_PATH = os.environ.get("DATABASE_PATH", "./menuapp.db")
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

# Polite scraping defaults - keep low to avoid hammering third-party sites.
REQUEST_TIMEOUT_SECONDS = 10
REQUEST_DELAY_SECONDS = 0.75
DEFAULT_MAX_PAGES_PER_SYNC = 300
USER_AGENT = "MenuappPersonalRecipeAggregator/1.0 (+self-hosted, single user)"

# Recipe pages older than this are re-fetched on a full re-sync.
STALE_AFTER_DAYS = 30
