import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional

from lekivpn.core import config, db

logger = logging.getLogger(__name__)


def _row_to_plan(row: Any) -> Dict[str, Any]:
    if isinstance(row, dict):
        d = {
            "plan_key": row["plan_key"],
            "name": row["name"],
            "description": row["description"],
            "amount": int(row["amount"]),
            "duration_days": int(row["duration_days"]),
            "sort_order": int(row["sort_order"]),
        }
        raw_usdt = row.get("amount_usdt")
    else:
        d = {
            "plan_key": row[0],
            "name": row[1],
            "description": row[2],
            "amount": int(row[3]),
            "duration_days": int(row[5]),
            "sort_order": int(row[6]),
        }
        raw_usdt = row[4]

    if raw_usdt is None:
        d["amount_usdt"] = None
    elif isinstance(raw_usdt, Decimal):
        d["amount_usdt"] = float(raw_usdt)
    else:
        d["amount_usdt"] = float(raw_usdt)
    return d


async def list_active_site_tariffs() -> List[Dict[str, Any]]:
    if not db.pool:
        return []
    try:
        async with db.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    f"""SELECT plan_key, name, description, amount, amount_usdt,
                               duration_days, sort_order
                        FROM {config.SITE_TARIFFS_TABLE}
                        WHERE is_active = 1
                        ORDER BY sort_order ASC, plan_key ASC"""
                )
                rows = await cursor.fetchall()
        return [_row_to_plan(r) for r in (rows or [])]
    except Exception as e:
        logger.exception("list_active_site_tariffs: %s", e)
        return []


async def get_site_tariff(plan_key: str) -> Optional[Dict[str, Any]]:
    if not db.pool or not plan_key:
        return None
    try:
        async with db.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    f"""SELECT plan_key, name, description, amount, amount_usdt,
                               duration_days, sort_order
                        FROM {config.SITE_TARIFFS_TABLE}
                        WHERE plan_key = %s AND is_active = 1 LIMIT 1""",
                    (plan_key,),
                )
                row = await cursor.fetchone()
        if not row:
            return None
        return _row_to_plan(row)
    except Exception as e:
        logger.exception("get_site_tariff: %s", e)
        return None
