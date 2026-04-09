import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from remnawave.enums.users import UserStatus

from lekivpn.schemas import telegram as models
from lekivpn.services import server as server_handler
from lekivpn.services import user_site_database, vpn

logger = logging.getLogger(__name__)


def _tid(site_user_id: int) -> str:
    return user_site_database.panel_telegram_id(site_user_id)


async def add_vpn_order_site(site_user_id: int, duration_days: int) -> Optional[str]:
    try:
        if not await user_site_database.user_exists(site_user_id):
            logger.warning("Site user not found: %s", site_user_id)
            return None
        api = server_handler.api
        tid = _tid(site_user_id)
        req = models.VpnOrderRequest(telegram_id=tid, duration_days=duration_days)
        device_id = await vpn.get_last_device_id(api, tid)
        return await vpn.add_user_async(api, req, device_id)
    except Exception as e:
        logger.exception("add_vpn_order_site: %s", e)
        return None


async def extend_vpn_order_site(site_user_id: int, device_id: int, duration_days: int) -> bool:
    try:
        if not await user_site_database.user_exists(site_user_id):
            return False
        user = models.VpnExtendRequest(
            telegram_id=_tid(site_user_id),
            device_id=device_id,
            duration_days=duration_days,
        )
        vpn_req = models.VpnRequest(telegram_id=user.telegram_id, device_id=user.device_id)
        if not await server_handler.is_exist_order(vpn_req):
            return False
        api = server_handler.api
        username = vpn.get_username(user.telegram_id, user.device_id)
        status = await vpn.extend_user_async(api, username, user.duration_days + 1)
        return bool(status)
    except Exception as e:
        logger.exception("extend_vpn_order_site: %s", e)
        return False


async def get_vpn_key_site(site_user_id: int, device_id: int):
    try:
        if not await user_site_database.user_exists(site_user_id):
            return False
        user = models.VpnRequest(telegram_id=_tid(site_user_id), device_id=device_id)
        if not await server_handler.is_exist_order(user):
            return False
        api = server_handler.api
        username = vpn.get_username(user.telegram_id, user.device_id)
        vpn_key = await vpn.get_subscription_async(api, username)
        if not vpn_key:
            return False
        return vpn_key
    except Exception as e:
        logger.exception("get_vpn_key_site: %s", e)
        return False


async def get_order_expiry_date_site(site_user_id: int, device_id: int) -> Optional[str]:
    try:
        if not await user_site_database.user_exists(site_user_id):
            return None
        user = models.VpnRequest(telegram_id=_tid(site_user_id), device_id=device_id)
        if not await server_handler.is_exist_order(user):
            return None
        tid = _tid(site_user_id)
        api = server_handler.api
        expiry_date = await vpn.get_device_expiry_date(api, vpn.get_username(tid, device_id))
        return expiry_date
    except Exception as e:
        logger.exception("get_order_expiry_date_site: %s", e)
        return None


async def get_active_devices_site(site_user_id: int) -> Any:
    try:
        tid = _tid(site_user_id)
        api = server_handler.api
        return await vpn.get_all_active_orders(api, tid)
    except Exception as e:
        logger.exception("get_active_devices_site: %s", e)
        return False


async def get_new_device_id_site(site_user_id: int):
    try:
        tid = _tid(site_user_id)
        api = server_handler.api
        return await vpn.get_last_device_id(api, tid)
    except Exception as e:
        logger.exception("get_new_device_id_site: %s", e)
        return False


def _dt_iso(dt: Any) -> Optional[str]:
    if dt is None:
        return None
    if isinstance(dt, datetime):
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc).isoformat()
        return dt.isoformat()
    return str(dt)


async def get_subscription_overview_site(site_user_id: int) -> Optional[Dict[str, Any]]:
    """
    Платежи из payments_site + подписки/URL с Remnawave (один запрос get_users_by_telegram_id).
    """
    if not await user_site_database.user_exists(site_user_id):
        return None

    tid = _tid(site_user_id)
    payments_raw = await user_site_database.list_payments_site(site_user_id, limit=50)
    payments: List[Dict[str, Any]] = []
    for p in payments_raw:
        payments.append(
            {
                **p,
                "created_at": _dt_iso(p.get("created_at")) or "",
            }
        )

    subscriptions: List[Dict[str, Any]] = []
    panel_reachable = False
    has_active_vpn = False
    now = datetime.now(timezone.utc)

    try:
        api = server_handler.api
        users_wrapped = await api.users.get_users_by_telegram_id(tid)
        panel_reachable = True
        for u in users_wrapped:
            if not u.username.startswith(f"{tid}_"):
                continue
            parts = u.username.split("_")
            try:
                device_id = int(parts[-1])
            except ValueError:
                continue
            exp = u.expire_at
            if exp is None:
                exp_aware = None
            elif exp.tzinfo is None:
                exp_aware = exp.replace(tzinfo=timezone.utc)
            else:
                exp_aware = exp
            active = u.status == UserStatus.ACTIVE and exp_aware is not None and exp_aware > now
            if active:
                has_active_vpn = True
            subscriptions.append(
                {
                    "device_id": device_id,
                    "username": u.username,
                    "subscription_url": u.subscription_url or "",
                    "expire_at": _dt_iso(exp),
                    "status": str(u.status),
                }
            )
        subscriptions.sort(key=lambda x: x["device_id"])
    except Exception as e:
        logger.exception("get_subscription_overview_site panel: %s", e)

    return {
        "site_user_id": site_user_id,
        "panel_telegram_id": tid,
        "panel_reachable": panel_reachable,
        "has_active_vpn": has_active_vpn,
        "subscriptions": subscriptions,
        "payments": payments,
    }
