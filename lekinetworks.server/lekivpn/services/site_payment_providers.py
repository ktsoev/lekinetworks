import asyncio
import logging
import os
import uuid
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import httpx

logger = logging.getLogger(__name__)

CRYPTOBOT_BASE = "https://pay.crypt.bot/api"
OXP_BASE = "https://app.0xprocessing.com"

METADATA_TYPE_SITE = "site_subscription"


def yookassa_configured() -> bool:
    return bool(os.getenv("YOOKASSA_SHOP_ID") and os.getenv("YOOKASSA_SECRET_KEY"))


def cryptobot_configured() -> bool:
    return bool(os.getenv("CRYPTOBOT_TOKEN"))


def oxprocessing_configured() -> bool:
    return bool(os.getenv("OXP_MERCHANT_ID"))


def _yookassa_configure() -> None:
    from yookassa import Configuration

    Configuration.account_id = os.environ["YOOKASSA_SHOP_ID"]
    Configuration.secret_key = os.environ["YOOKASSA_SECRET_KEY"]


async def create_yookassa_checkout(
    *,
    site_user_id: int,
    plan_key: str,
    tariff: Dict[str, Any],
    receipt_email: str,
    return_url: str,
    extend: bool = False,
    extend_device_id: Optional[int] = None,
) -> Dict[str, Any]:
    if not yookassa_configured():
        raise RuntimeError("YooKassa is not configured (YOOKASSA_SHOP_ID / YOOKASSA_SECRET_KEY)")
    amount_rub = float(tariff["amount"])
    if amount_rub <= 0:
        raise ValueError("plan amount must be positive for paid checkout")

    from yookassa import Payment

    invoice_id = str(uuid.uuid4())
    _yookassa_configure()
    payment_data = {
        "amount": {"value": f"{amount_rub:.2f}", "currency": "RUB"},
        "confirmation": {"type": "redirect", "return_url": return_url},
        "capture": True,
        "description": f"LEKI Networks {plan_key} user {site_user_id}",
        "receipt": {
            "customer": {"email": receipt_email},
            "items": [
                {
                    "description": f"Подписка {plan_key}, {tariff['duration_days']} дн.",
                    "quantity": "1",
                    "amount": {"value": f"{amount_rub:.2f}", "currency": "RUB"},
                    "vat_code": 1,
                    "payment_subject": "service",
                    "payment_mode": "full_payment",
                }
            ],
        },
        "metadata": {
            "invoice_id": invoice_id,
            "site_user_id": str(site_user_id),
            "plan_key": plan_key,
            "type": METADATA_TYPE_SITE,
            "extend": "1" if extend else "0",
            "device_id": str(extend_device_id) if extend and extend_device_id is not None else "",
        },
    }

    def _create():
        try:
            return Payment.create(payment_data, idempotency_key=invoice_id)
        except TypeError:
            return Payment.create(payment_data)

    try:
        payment = await asyncio.to_thread(_create)
    except Exception as e:
        logger.exception("YooKassa create: %s", e)
        raise RuntimeError(f"YooKassa create failed: {e}") from e

    url = payment.confirmation.confirmation_url if payment.confirmation else None
    if not url:
        raise RuntimeError("YooKassa: no confirmation URL")

    return {
        "invoice_id": invoice_id,
        "provider_payment_id": payment.id,
        "payment_url": url,
        "amount": amount_rub,
        "currency": "RUB",
    }


async def create_cryptobot_checkout(
    *,
    site_user_id: int,
    plan_key: str,
    tariff: Dict[str, Any],
    return_url: str,
) -> Dict[str, Any]:
    token = os.getenv("CRYPTOBOT_TOKEN")
    if not token:
        raise RuntimeError("CryptoBot is not configured (CRYPTOBOT_TOKEN)")
    usd = float(tariff.get("amount_usdt") or 0)
    if usd <= 0:
        raise ValueError("plan USDT amount must be positive for CryptoBot")

    payload = f"{site_user_id}|{plan_key}"
    invoice_data = {
        "currency_type": "fiat",
        "fiat": "USD",
        "amount": f"{usd:.2f}",
        "swap_to": "USDT",
        "description": f"LEKI Networks {plan_key}",
        "paid_btn_name": "callback",
        "paid_btn_url": return_url,
        "payload": payload,
        "expires_in": 600,
    }
    headers = {"Crypto-Pay-API-Token": token}
    async with httpx.AsyncClient(base_url=CRYPTOBOT_BASE, timeout=30.0) as client:
        resp = await client.post("/createInvoice", json=invoice_data, headers=headers)
        resp.raise_for_status()
        body = resp.json()
        if not body.get("ok"):
            raise RuntimeError(f"CryptoBot: {body}")
        result = body["result"]

    invoice_id = str(result["invoice_id"])
    pay_url = result.get("mini_app_invoice_url") or result.get("pay_url")
    if not pay_url:
        raise RuntimeError("CryptoBot: no payment URL in response")

    return {
        "invoice_id": invoice_id,
        "provider_payment_id": invoice_id,
        "payment_url": pay_url,
        "amount": usd,
        "currency": "USD",
    }


def create_oxprocessing_checkout(
    *,
    site_user_id: int,
    plan_key: str,
    tariff: Dict[str, Any],
    return_url: str,
    email: Optional[str],
) -> Dict[str, Any]:
    merchant = os.getenv("OXP_MERCHANT_ID")
    if not merchant:
        raise RuntimeError("0xProcessing is not configured (OXP_MERCHANT_ID)")
    usd = float(tariff.get("amount_usdt") or 0)
    if usd <= 0:
        raise ValueError("plan USDT amount must be positive for 0xProcessing")

    invoice_id = str(uuid.uuid4())
    query: Dict[str, str] = {
        "MerchantId": merchant,
        "AmountUsd": f"{usd:.2f}",
        "BillingID": invoice_id,
        "ClientId": str(site_user_id),
        "SuccessUrl": return_url,
        "CancelUrl": return_url,
        "AutoReturn": "true",
    }
    if email:
        query["Email"] = email
    if os.getenv("OXP_TEST_PAYMENT", "").lower() in ("1", "true", "yes"):
        query["Test"] = "true"

    payment_url = f"{OXP_BASE}/payment/create/?{urlencode(query)}"
    return {
        "invoice_id": invoice_id,
        "provider_payment_id": invoice_id,
        "payment_url": payment_url,
        "amount": usd,
        "currency": "USD",
    }
