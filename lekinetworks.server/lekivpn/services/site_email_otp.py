import hashlib
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone

from lekivpn.core import config, db

logger = logging.getLogger(__name__)

_MAX_ATTEMPTS = 5


def _pepper() -> str:
    return os.getenv("OTP_PEPPER") or os.getenv("JWT_SECRET") or "dev-insecure-pepper"


def _hash_code(email: str, code: str) -> str:
    raw = f"{email}:{code}:{_pepper()}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


async def save_otp(email: str, code: str, ttl_minutes: int) -> bool:
    if not db.pool:
        return False
    code_hash = _hash_code(email, code)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes)
    expires_naive = expires_at.replace(tzinfo=None)
    try:
        async with db.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    f"""REPLACE INTO {config.SITE_EMAIL_OTP_TABLE}
                        (email, code_hash, expires_at, attempts)
                        VALUES (%s, %s, %s, 0)""",
                    (email, code_hash, expires_naive),
                )
        return True
    except Exception as e:
        logger.exception("save_otp: %s", e)
        return False


async def verify_otp(email: str, code: str) -> bool:
    if not db.pool:
        return False
    try:
        async with db.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    f"""SELECT code_hash, expires_at, attempts
                        FROM {config.SITE_EMAIL_OTP_TABLE} WHERE email = %s""",
                    (email,),
                )
                row = await cursor.fetchone()
                if not row:
                    return False
                if isinstance(row, dict):
                    stored_hash = row["code_hash"]
                    expires_at = row["expires_at"]
                    attempts = int(row["attempts"] or 0)
                else:
                    stored_hash, expires_at, attempts = row[0], row[1], int(row[2] or 0)

                if attempts >= _MAX_ATTEMPTS:
                    return False

                now = datetime.now(timezone.utc).replace(tzinfo=None)
                if isinstance(expires_at, datetime) and expires_at.tzinfo:
                    exp_cmp = expires_at.replace(tzinfo=None)
                else:
                    exp_cmp = expires_at
                if not exp_cmp or now > exp_cmp:
                    await cursor.execute(
                        f"DELETE FROM {config.SITE_EMAIL_OTP_TABLE} WHERE email = %s",
                        (email,),
                    )
                    return False

                expect = _hash_code(email, code)
                if not secrets.compare_digest(str(stored_hash), expect):
                    await cursor.execute(
                        f"""UPDATE {config.SITE_EMAIL_OTP_TABLE}
                            SET attempts = attempts + 1 WHERE email = %s""",
                        (email,),
                    )
                    return False

                await cursor.execute(
                    f"DELETE FROM {config.SITE_EMAIL_OTP_TABLE} WHERE email = %s",
                    (email,),
                )
                return True
    except Exception as e:
        logger.exception("verify_otp: %s", e)
        return False
