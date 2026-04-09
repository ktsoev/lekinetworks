import os
from functools import lru_cache

import httpx
from dotenv import load_dotenv

load_dotenv()


@lru_cache
def backend_base_url() -> str:
    v = os.getenv("BACKEND_BASE_URL", "").rstrip("/")
    if not v:
        raise RuntimeError("BACKEND_BASE_URL is required")
    return v


@lru_cache
def server_api_key() -> str:
    v = os.getenv("SERVER_API_KEY", "")
    if not v:
        raise RuntimeError("SERVER_API_KEY is required")
    return v


def cors_origins() -> list[str]:
    raw = os.getenv("SITE_CORS_ORIGINS", "")
    return [o.strip() for o in raw.split(",") if o.strip()]


def request_code_rate_limit() -> str:
    return os.getenv("REQUEST_CODE_RATE_LIMIT", "5/minute")


def verify_code_rate_limit() -> str:
    return os.getenv("VERIFY_CODE_RATE_LIMIT", "10/minute")


def checkout_rate_limit() -> str:
    return os.getenv("CHECKOUT_RATE_LIMIT", "20/minute")


def site_write_rate_limit() -> str:
    return os.getenv("SITE_WRITE_RATE_LIMIT", "60/minute")


def subscription_overview_rate_limit() -> str:
    """Частые опросы с личного кабинета — отдельно от get-key / promocode."""
    return os.getenv("SUBSCRIPTION_OVERVIEW_RATE_LIMIT", "300/minute")


def site_read_rate_limit() -> str:
    return os.getenv("SITE_READ_RATE_LIMIT", "120/minute")


def max_request_body_bytes() -> int:
    v = os.getenv("MAX_REQUEST_BODY_BYTES", "1048576")
    try:
        n = int(v)
    except ValueError:
        return 1048576
    return max(1024, n)


def webhook_http_timeout() -> httpx.Timeout:
    connect = float(os.getenv("WEBHOOK_FORWARD_TIMEOUT_CONNECT", "5.0"))
    read = float(os.getenv("WEBHOOK_FORWARD_TIMEOUT_READ", "60.0"))
    return httpx.Timeout(connect=connect, read=read, write=read, pool=connect)
