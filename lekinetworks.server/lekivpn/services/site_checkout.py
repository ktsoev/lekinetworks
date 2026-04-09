import logging
from typing import Any, Dict, Optional

import pymysql.err

from lekivpn.core import config, db

logger = logging.getLogger(__name__)


async def insert_checkout_pending(
    invoice_id: str,
    provider: str,
    site_user_id: int,
    plan_key: str,
    *,
    extend_subscription: bool = False,
    extend_device_id: Optional[int] = None,
) -> bool:
    if not db.pool:
        return False
    ext = 1 if extend_subscription else 0
    dev = int(extend_device_id) if extend_device_id is not None else None
    try:
        async with db.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    f"""INSERT INTO {config.SITE_CHECKOUT_PENDING_TABLE}
                        (invoice_id, provider, site_user_id, plan_key,
                         extend_subscription, extend_device_id)
                        VALUES (%s, %s, %s, %s, %s, %s)""",
                    (invoice_id, provider, site_user_id, plan_key, ext, dev),
                )
        return True
    except Exception as e:
        logger.exception("insert_checkout_pending: %s", e)
        return False


async def get_checkout_pending(invoice_id: str) -> Optional[Dict[str, Any]]:
    if not db.pool or not invoice_id:
        return None
    try:
        async with db.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    f"""SELECT invoice_id, provider, site_user_id, plan_key,
                               extend_subscription, extend_device_id
                        FROM {config.SITE_CHECKOUT_PENDING_TABLE}
                        WHERE invoice_id = %s LIMIT 1""",
                    (invoice_id,),
                )
                row = await cursor.fetchone()
        if not row:
            return None
        if isinstance(row, dict):
            ext_dev = row.get("extend_device_id")
            return {
                "invoice_id": row["invoice_id"],
                "provider": row["provider"],
                "site_user_id": int(row["site_user_id"]),
                "plan_key": row["plan_key"],
                "extend_subscription": bool(int(row.get("extend_subscription") or 0)),
                "extend_device_id": int(ext_dev) if ext_dev is not None else None,
            }
        ext_dev = row[5] if len(row) > 5 else None
        return {
            "invoice_id": row[0],
            "provider": row[1],
            "site_user_id": int(row[2]),
            "plan_key": row[3],
            "extend_subscription": bool(int(row[4] if len(row) > 4 else 0)),
            "extend_device_id": int(ext_dev) if ext_dev is not None else None,
        }
    except Exception as e:
        logger.exception("get_checkout_pending: %s", e)
        return None


async def delete_checkout_pending(invoice_id: str) -> None:
    if not db.pool or not invoice_id:
        return
    try:
        async with db.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    f"DELETE FROM {config.SITE_CHECKOUT_PENDING_TABLE} WHERE invoice_id = %s",
                    (invoice_id,),
                )
    except Exception as e:
        logger.exception("delete_checkout_pending: %s", e)


async def claim_payment_idempotency(external_id: str) -> bool:
    """Return True if this webhook may proceed (new key). False if duplicate."""
    if not db.pool or not external_id:
        return False
    try:
        async with db.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    f"INSERT INTO {config.SITE_PAYMENT_IDEMPOTENCY_TABLE} (external_id) VALUES (%s)",
                    (external_id,),
                )
        return True
    except pymysql.err.IntegrityError:
        return False
    except Exception as e:
        logger.exception("claim_payment_idempotency: %s", e)
        return False


async def release_payment_idempotency(external_id: str) -> None:
    if not db.pool or not external_id:
        return
    try:
        async with db.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    f"DELETE FROM {config.SITE_PAYMENT_IDEMPOTENCY_TABLE} WHERE external_id = %s",
                    (external_id,),
                )
    except Exception as e:
        logger.exception("release_payment_idempotency: %s", e)
