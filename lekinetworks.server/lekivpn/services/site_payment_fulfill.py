import logging
from typing import Any, Dict, Optional, Tuple

from lekivpn.services import site_checkout, site_server, site_tariffs_database, user_site_database

logger = logging.getLogger(__name__)


async def fulfill_site_checkout(
    site_user_id: int,
    duration_days: int,
    *,
    extend: bool,
    extend_device_id: Optional[int],
) -> Tuple[bool, int]:
    """extend=False — новый ключ; extend=True — продление указанного device_id."""
    if extend:
        if extend_device_id is None or extend_device_id < 1:
            return False, -1
        ok = await site_server.extend_vpn_order_site(site_user_id, extend_device_id, duration_days)
        return (ok, extend_device_id if ok else -1)
    device_id = await site_server.get_new_device_id_site(site_user_id)
    if device_id is False:
        return False, -1
    dev = int(device_id)
    url = await site_server.add_vpn_order_site(site_user_id, duration_days)
    return (url is not None), dev if url else -1


def _log_amount_for_tariff(tariff: Dict[str, Any], payment_method: str) -> Tuple[int, str]:
    if payment_method == "yookassa":
        return int(tariff["amount"]), "RUB"
    usdt = float(tariff.get("amount_usdt") or 0)
    return int(round(usdt * 100)), "USDT"


async def complete_site_purchase_from_webhook(
    *,
    external_id: str,
    site_user_id: int,
    plan_key: str,
    payment_type: str,
    extend: bool = False,
    extend_device_id: Optional[int] = None,
) -> bool:
    """
    Idempotent: external_id is provider's unique payment id.
    """
    if not await user_site_database.user_exists(site_user_id):
        logger.error("webhook: site user %s missing", site_user_id)
        return False

    tariff = await site_tariffs_database.get_site_tariff(plan_key)
    if not tariff:
        logger.error("webhook: plan %s missing", plan_key)
        return False

    if extend and (extend_device_id is None or extend_device_id < 1):
        logger.error("webhook: extend without device_id user=%s plan=%s", site_user_id, plan_key)
        return False

    if not await site_checkout.claim_payment_idempotency(external_id):
        logger.info("webhook: duplicate external_id=%s", external_id)
        return True

    ok, device_id = await fulfill_site_checkout(
        site_user_id,
        tariff["duration_days"],
        extend=extend,
        extend_device_id=extend_device_id,
    )
    if not ok or device_id < 0:
        await site_checkout.release_payment_idempotency(external_id)
        logger.error("webhook: fulfill failed user=%s plan=%s", site_user_id, plan_key)
        return False

    log_amount, log_currency = _log_amount_for_tariff(tariff, payment_type)

    logged = await user_site_database.log_payment_site(
        site_user_id,
        log_amount,
        log_currency,
        plan_key,
        device_id,
        payment_type,
        external_id=external_id,
    )
    if not logged:
        logger.error("webhook: log_payment failed after fulfill external_id=%s", external_id)

    return True


async def complete_site_purchase_oxp(
    *,
    external_id: str,
    invoice_id: str,
) -> bool:
    """0xProcessing: resolve checkout by BillingID (invoice_id)."""
    pending = await site_checkout.get_checkout_pending(invoice_id)
    if not pending:
        if await user_site_database.payments_site_has_external(external_id):
            return True
        logger.error("oxp webhook: pending invoice %s not found", invoice_id)
        return False
    ok = await complete_site_purchase_from_webhook(
        external_id=external_id,
        site_user_id=pending["site_user_id"],
        plan_key=pending["plan_key"],
        payment_type="oxprocessing",
        extend=bool(pending.get("extend_subscription")),
        extend_device_id=pending.get("extend_device_id"),
    )
    if ok:
        await site_checkout.delete_checkout_pending(invoice_id)
    return ok
