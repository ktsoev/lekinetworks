import logging
import os
import re
from typing import Any, Dict, Optional

import pymysql.err

from lekivpn.core import config, db

logger = logging.getLogger(__name__)

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def is_valid_email(email: str) -> bool:
    e = normalize_email(email)
    return bool(e) and _EMAIL_RE.match(e) is not None


def _site_panel_telegram_base() -> int:
    raw = (os.getenv("SITE_PANEL_TELEGRAM_ID_BASE") or "").strip()
    if raw:
        return int(raw)
    return config.SITE_PANEL_TELEGRAM_ID_BASE


def panel_telegram_id(site_user_id: int) -> str:
    """Numeric string for Remnawave /users/by-telegram-id/ (panel expects int-sized ids)."""
    return str(_site_panel_telegram_base() + site_user_id)


async def user_exists(site_user_id: int) -> bool:
    if not db.pool:
        return False
    try:
        async with db.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    f"SELECT 1 FROM {config.USERS_SITE_TABLE} WHERE id = %s LIMIT 1",
                    (site_user_id,),
                )
                row = await cursor.fetchone()
                return bool(row)
    except Exception as e:
        logger.exception("user_exists site: %s", e)
        return False


async def get_user_by_id(site_user_id: int) -> Optional[Dict[str, Any]]:
    if not db.pool:
        return None
    try:
        async with db.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    f"SELECT id, email FROM {config.USERS_SITE_TABLE} WHERE id = %s",
                    (site_user_id,),
                )
                row = await cursor.fetchone()
                if not row:
                    return None
                if isinstance(row, dict):
                    return {"id": row["id"], "email": row["email"]}
                return {"id": row[0], "email": row[1]}
    except Exception as e:
        logger.exception("get_user_by_id site: %s", e)
        return None


async def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    if not db.pool:
        return None
    e = normalize_email(email)
    try:
        async with db.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    f"SELECT id, email FROM {config.USERS_SITE_TABLE} WHERE email = %s",
                    (e,),
                )
                row = await cursor.fetchone()
                if not row:
                    return None
                if isinstance(row, dict):
                    return {"id": row["id"], "email": row["email"]}
                return {"id": row[0], "email": row[1]}
    except Exception as e:
        logger.exception("get_user_by_email site: %s", e)
        return None


async def create_user(email: str) -> int | None:
    if not db.pool:
        return None
    e = normalize_email(email)
    try:
        async with db.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    f"INSERT INTO {config.USERS_SITE_TABLE} (email) VALUES (%s)",
                    (e,),
                )
                return cursor.lastrowid
    except Exception as ex:
        logger.exception("create_user site: %s", ex)
        return None


async def get_or_create_user_by_email(email: str) -> Optional[int]:
    existing = await get_user_by_email(email)
    if existing:
        return int(existing["id"])
    uid = await create_user(email)
    if uid:
        return int(uid)
    existing = await get_user_by_email(email)
    return int(existing["id"]) if existing else None


async def list_payments_site(site_user_id: int, limit: int = 50) -> list[Dict[str, Any]]:
    if not db.pool:
        return []
    lim = max(1, min(int(limit), 200))
    try:
        async with db.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    f"""SELECT id, amount, currency, product_id, device_id, payment_type,
                               external_id, created_at
                        FROM {config.PAYMENTS_SITE_TABLE}
                        WHERE site_user_id = %s
                        ORDER BY created_at DESC
                        LIMIT %s""",
                    (site_user_id, lim),
                )
                rows = await cursor.fetchall()
        out: list[Dict[str, Any]] = []
        for row in rows or []:
            if isinstance(row, dict):
                created = row["created_at"]
                out.append(
                    {
                        "id": int(row["id"]),
                        "amount": int(row["amount"]),
                        "currency": str(row["currency"]),
                        "product_id": str(row["product_id"]),
                        "device_id": int(row["device_id"]),
                        "payment_type": str(row["payment_type"]),
                        "external_id": row.get("external_id"),
                        "created_at": created,
                    }
                )
            else:
                created = row[7]
                out.append(
                    {
                        "id": int(row[0]),
                        "amount": int(row[1]),
                        "currency": str(row[2]),
                        "product_id": str(row[3]),
                        "device_id": int(row[4]),
                        "payment_type": str(row[5]),
                        "external_id": row[6],
                        "created_at": created,
                    }
                )
        return out
    except Exception as e:
        logger.exception("list_payments_site: %s", e)
        return []


async def payments_site_has_external(external_id: str) -> bool:
    if not db.pool or not external_id:
        return False
    try:
        async with db.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    f"SELECT 1 FROM {config.PAYMENTS_SITE_TABLE} WHERE external_id = %s LIMIT 1",
                    (external_id,),
                )
                row = await cursor.fetchone()
        return bool(row)
    except Exception as e:
        logger.exception("payments_site_has_external: %s", e)
        return False


async def log_payment_site(
    site_user_id: int,
    amount: int,
    currency: str,
    product_id: str,
    device_id: int,
    payment_type: str,
    external_id: Optional[str] = None,
) -> bool:
    if not db.pool:
        return False
    ext = (external_id or "").strip() or None
    try:
        async with db.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    f"""INSERT INTO {config.PAYMENTS_SITE_TABLE}
                        (site_user_id, amount, currency, product_id, device_id, payment_type, external_id)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    (
                        site_user_id,
                        amount,
                        currency,
                        product_id,
                        device_id,
                        payment_type,
                        ext,
                    ),
                )
        return True
    except pymysql.err.IntegrityError as exc:
        if exc.args and exc.args[0] == 1062 and ext:
            logger.info("log_payment_site duplicate external_id=%s, idempotent ok", ext)
            return True
        logger.exception("log_payment_site integrity: %s", exc)
        return False
    except Exception as e:
        logger.exception("log_payment_site: %s", e)
        return False
