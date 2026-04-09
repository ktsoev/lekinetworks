import os
from datetime import datetime, timezone
from typing import Any

import jwt

_ALG = "HS256"


def _secret() -> str:
    s = os.getenv("JWT_SECRET")
    if not s:
        raise RuntimeError("JWT_SECRET environment variable is required for site auth")
    return s


def create_access_token(site_user_id: int) -> str:
    expire_min = int(os.getenv("JWT_EXPIRE_MINUTES", str(60 * 24 * 7)))
    now = int(datetime.now(timezone.utc).timestamp())
    payload: dict[str, Any] = {
        "sub": str(site_user_id),
        "iat": now,
        "exp": now + expire_min * 60,
    }
    return jwt.encode(payload, _secret(), algorithm=_ALG)


def decode_access_token(token: str) -> int:
    data = jwt.decode(token, _secret(), algorithms=[_ALG])
    sub = data.get("sub")
    if sub is None:
        raise jwt.InvalidTokenError("missing sub")
    return int(sub)
