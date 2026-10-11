"""Superset configuration for Railway (web, Celery worker, Celery beat, init).

Everything environment-specific comes from variables, so the same image runs
every role. Loaded by Superset because /app/pythonpath is on PYTHONPATH.
"""

from __future__ import annotations

import os
from urllib.parse import urlparse

from celery.schedules import crontab
from flask_caching.backends.rediscache import RedisCache


def _required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Environment variable {name} must be set")
    return value


def _flag(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


# --- Core -------------------------------------------------------------------
SECRET_KEY = _required("SUPERSET_SECRET_KEY")

_db_url = _required("SUPERSET_DATABASE_URL")
if _db_url.startswith("postgres://"):
    _db_url = "postgresql://" + _db_url[len("postgres://"):]
SQLALCHEMY_DATABASE_URI = _db_url
SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

# Served behind Railway's HTTPS proxy.
ENABLE_PROXY_FIX = True
PREFERRED_URL_SCHEME = "https"
SESSION_COOKIE_SECURE = _flag("SUPERSET_SESSION_COOKIE_SECURE", True)
SUPERSET_WEBSERVER_TIMEOUT = int(os.environ.get("SUPERSET_WEBSERVER_TIMEOUT", "120"))

# --- Redis: broker, results, caches, rate limiting ---------------------------
_redis = _required("SUPERSET_REDIS_URL").rstrip("/")
_redis_parts = urlparse(_redis)


def _redis_db(index: int) -> str:
    return f"{_redis}/{index}"


def _cache(index: int, prefix: str, timeout: int) -> dict:
    return {
        "CACHE_TYPE": "RedisCache",
        "CACHE_DEFAULT_TIMEOUT": timeout,
        "CACHE_KEY_PREFIX": prefix,
        "CACHE_REDIS_URL": _redis_db(index),
    }


CACHE_CONFIG = _cache(2, "superset_meta_", 300)
DATA_CACHE_CONFIG = _cache(3, "superset_data_", 86400)
FILTER_STATE_CACHE_CONFIG = _cache(4, "superset_filter_", 86400)
EXPLORE_FORM_DATA_CACHE_CONFIG = _cache(5, "superset_explore_", 86400)
THUMBNAIL_CACHE_CONFIG = _cache(6, "superset_thumb_", 86400)

# Async SQL Lab results (used when "Asynchronous query execution" is enabled on a database).
RESULTS_BACKEND = RedisCache(
    host=_redis_parts.hostname,
    port=_redis_parts.port or 6379,
    password=_redis_parts.password,
    db=7,
    key_prefix="superset_results",
)

RATELIMIT_STORAGE_URI = _redis_db(8)


class CeleryConfig:
    broker_url = _redis_db(0)
    result_backend = _redis_db(1)
    imports = (
        "superset.sql_lab",
        "superset.tasks.scheduler",
        "superset.tasks.thumbnails",
        "superset.tasks.cache",
    )
    worker_prefetch_multiplier = 1
    task_acks_late = False
    broker_connection_retry_on_startup = True
    beat_schedule = {
        "reports.scheduler": {
            "task": "reports.scheduler",
            "schedule": crontab(minute="*", hour="*"),
        },
        "reports.prune_log": {
            "task": "reports.prune_log",
            "schedule": crontab(minute=10, hour=0),
        },
    }


CELERY_CONFIG = CeleryConfig

# --- Features ----------------------------------------------------------------
FEATURE_FLAGS = {
    "ALERT_REPORTS": _flag("SUPERSET_ALERT_REPORTS", True),
    "PLAYWRIGHT_REPORTS_AND_THUMBNAILS": True,
    "THUMBNAILS": _flag("SUPERSET_THUMBNAILS", False),
}

# The worker renders dashboards for reports through the web service on the
# private network; links in emails use the public URL.
WEBDRIVER_BASEURL = os.environ.get("SUPERSET_WEBDRIVER_BASEURL", "http://localhost:8088/")
WEBDRIVER_BASEURL_USER_FRIENDLY = os.environ.get("SUPERSET_PUBLIC_URL", WEBDRIVER_BASEURL)

# --- Email (optional) --------------------------------------------------------
SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587") or 587)
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
SMTP_MAIL_FROM = os.environ.get("SMTP_MAIL_FROM", "superset@example.com")
SMTP_STARTTLS = _flag("SMTP_STARTTLS", True)
SMTP_SSL = _flag("SMTP_SSL", False)
# Without SMTP, reports are logged instead of sent.
ALERT_REPORTS_NOTIFICATION_DRY_RUN = not SMTP_HOST

# --- Logging -----------------------------------------------------------------
LOG_LEVEL = os.environ.get("SUPERSET_LOG_LEVEL", "INFO").upper()
