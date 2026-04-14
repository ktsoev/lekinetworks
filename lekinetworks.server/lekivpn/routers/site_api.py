import hashlib
import hmac
import json
import logging
import os
import secrets
from ipaddress import ip_address, ip_network
from typing import Optional

import jwt
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from lekivpn.routers.deps import require_api_key
from lekivpn.schemas import site as models_site
from lekivpn.services import (
    servers_database,
    site_checkout,
    site_email_otp,
    site_jwt,
    site_mail,
    site_payment_fulfill,
    site_payment_providers,
    site_server,
    site_tariffs_database,
    user_site_database,
)

logger = logging.getLogger(__name__)

router = APIRouter()
security = HTTPBearer(auto_error=False)


def _otp_ttl_minutes() -> int:
    return int(os.getenv("OTP_EXPIRE_MINUTES", "15"))


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for") or request.headers.get("X-Forwarded-For")
    if fwd:
        return fwd.split(",")[0].strip()
    if request.client:
        return request.client.host
    return ""


def _yookassa_ip_allowed(ip: str) -> bool:
    networks = [
        "185.71.76.0/27",
        "185.71.77.0/27",
        "77.75.153.0/25",
        "77.75.156.11/32",
        "77.75.156.35/32",
        "77.75.154.128/25",
        "2a02:5180::/32",
    ]
    try:
        addr = ip_address(ip)
        return any(addr in ip_network(net) for net in networks)
    except ValueError:
        return False


async def get_site_user_id(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> int:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        return site_jwt.decode_access_token(credentials.credentials)
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


@router.post("/auth/request-code")
async def site_request_code(
    body: models_site.SiteRequestCodeBody,
    _: None = Depends(require_api_key),
):
    email = user_site_database.normalize_email(body.email)
    if not user_site_database.is_valid_email(email):
        raise HTTPException(status_code=400, detail="Invalid email")

    from lekivpn.core import db

    if not db.pool:
        raise HTTPException(status_code=503, detail="Database unavailable")

    code = f"{secrets.randbelow(10**6):06d}"
    if not await site_email_otp.save_otp(email, code, _otp_ttl_minutes()):
        raise HTTPException(status_code=500, detail="Failed to save OTP")

    try:
        await site_mail.send_login_code(email, code)
    except Exception as e:
        logger.exception("send_login_code: %s", e)
        raise HTTPException(status_code=500, detail="Failed to send email")

    return {}


@router.post("/auth/verify-code", response_model=models_site.SiteTokenResponse)
async def site_verify_code(
    body: models_site.SiteVerifyCodeBody,
    _: None = Depends(require_api_key),
):
    email = user_site_database.normalize_email(body.email)
    code = body.code.strip().replace(" ", "")
    logger.info("verify-code attempt: email=%s code_len=%d", email, len(code))
    if not user_site_database.is_valid_email(email):
        logger.warning("verify-code: invalid email format email=%s", email)
        raise HTTPException(status_code=400, detail="Invalid email")
    if not code:
        logger.warning("verify-code: empty code for email=%s", email)
        raise HTTPException(status_code=400, detail="Invalid code")

    if not await site_email_otp.verify_otp(email, code):
        logger.warning("verify-code: rejected for email=%s", email)
        raise HTTPException(status_code=400, detail="Invalid or expired code")

    site_user_id = await user_site_database.get_or_create_user_by_email(email)
    if not site_user_id:
        logger.error("verify-code: failed to get/create user for email=%s", email)
        raise HTTPException(status_code=500, detail="Failed to create user")

    token = site_jwt.create_access_token(site_user_id)
    logger.info("verify-code: login success email=%s site_user_id=%s", email, site_user_id)
    return models_site.SiteTokenResponse(access_token=token)


@router.get("/auth/me", response_model=models_site.SiteMeResponse)
async def site_me(
    site_user_id: int = Depends(get_site_user_id),
    _: None = Depends(require_api_key),
):
    user = await user_site_database.get_user_by_id(site_user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return models_site.SiteMeResponse(id=user["id"], email=user["email"])


@router.post("/vpn/add-order")
async def site_add_vpn_order(
    body: models_site.SiteVpnOrderBody,
    _: None = Depends(require_api_key),
):
    url = await site_server.add_vpn_order_site(body.site_user_id, body.duration_days)
    if not url:
        raise HTTPException(status_code=400, detail="Could not create order")
    return {"vpn_url": url}


@router.post("/vpn/extend-order")
async def site_extend_vpn(
    body: models_site.SiteVpnExtendBody,
    site_user_id: int = Depends(get_site_user_id),
    _: None = Depends(require_api_key),
):
    ok = await site_server.extend_vpn_order_site(site_user_id, body.device_id, body.duration_days)
    if not ok:
        raise HTTPException(status_code=400, detail="Could not extend order")
    return {"ok": True}


@router.post("/vpn/get-key")
async def site_get_vpn_key(
    body: models_site.SiteVpnDeviceBody,
    site_user_id: int = Depends(get_site_user_id),
    _: None = Depends(require_api_key),
):
    key = await site_server.get_vpn_key_site(site_user_id, body.device_id)
    if not key:
        raise HTTPException(status_code=404, detail="Key not found")
    return {"vpn_key": key}


@router.post("/vpn/get-orders")
async def site_get_orders(
    site_user_id: int = Depends(get_site_user_id),
    _: None = Depends(require_api_key),
):
    devices = await site_server.get_active_devices_site(site_user_id)
    if devices is False or devices is None:
        raise HTTPException(status_code=500, detail="Failed to load orders")
    return devices


@router.post("/vpn/get-new-device-id")
async def site_get_new_device_id(
    site_user_id: int = Depends(get_site_user_id),
    _: None = Depends(require_api_key),
):
    device_id = await site_server.get_new_device_id_site(site_user_id)
    if device_id is False:
        raise HTTPException(status_code=500, detail="Failed to get device id")
    return {"device_id": device_id}


@router.post("/vpn/get-expiry")
async def site_get_expiry(
    body: models_site.SiteVpnDeviceBody,
    site_user_id: int = Depends(get_site_user_id),
    _: None = Depends(require_api_key),
):
    expiry = await site_server.get_order_expiry_date_site(site_user_id, body.device_id)
    if expiry is None:
        raise HTTPException(status_code=404, detail="Expiry not found")
    return {"expiry_date": expiry}


@router.post("/promocode/activate")
async def site_activate_promocode(
    body: models_site.SitePromocodeBody,
    site_user_id: int = Depends(get_site_user_id),
    _: None = Depends(require_api_key),
):
    resp = await servers_database.activate_promocode_site(site_user_id, body.promocode)
    if not resp:
        raise HTTPException(status_code=400, detail="Invalid promocode or activation failed")
    if hasattr(resp, "model_dump"):
        return resp.model_dump()
    return resp.dict()


@router.get("/plans")
async def site_plans_list(_: None = Depends(require_api_key)):
    return await site_tariffs_database.list_active_site_tariffs()


@router.post(
    "/subscription/overview",
    response_model=models_site.SiteSubscriptionOverviewResponse,
)
async def site_subscription_overview(
    site_user_id: int = Depends(get_site_user_id),
    _: None = Depends(require_api_key),
):
    overview = await site_server.get_subscription_overview_site(site_user_id)
    if overview is None:
        raise HTTPException(status_code=404, detail="User not found")
    return models_site.SiteSubscriptionOverviewResponse(**overview)


@router.post("/payment/log")
async def site_log_payment(
    body: models_site.SitePaymentLogBody,
    _: None = Depends(require_api_key),
):
    if not await user_site_database.user_exists(body.site_user_id):
        raise HTTPException(status_code=404, detail="User not found")
    ok = await user_site_database.log_payment_site(
        body.site_user_id,
        body.amount,
        body.currency,
        body.product_id,
        body.device_id,
        body.payment_type,
        external_id=body.external_id,
    )
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to log payment")
    return {}


async def _checkout_common(site_user_id: int, body: models_site.SiteCheckoutBody, provider: str):
    tariff = await site_tariffs_database.get_site_tariff(body.plan_key)
    if not tariff:
        raise HTTPException(status_code=404, detail="Unknown plan")
    if int(tariff["amount"]) <= 0 and provider == "yookassa":
        raise HTTPException(status_code=400, detail="Plan is not payable via YooKassa")
    user = await user_site_database.get_user_by_id(site_user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    receipt_email = (body.email or user["email"] or "").strip()
    if provider == "yookassa" and not user_site_database.is_valid_email(receipt_email):
        raise HTTPException(status_code=400, detail="Valid email required for YooKassa receipt")


@router.post("/payment/checkout/yookassa", response_model=models_site.SiteCheckoutResponse)
async def checkout_yookassa(
    body: models_site.SiteCheckoutBody,
    site_user_id: int = Depends(get_site_user_id),
    _: None = Depends(require_api_key),
):
    await _checkout_common(site_user_id, body, "yookassa")
    tariff = await site_tariffs_database.get_site_tariff(body.plan_key)
    user = await user_site_database.get_user_by_id(site_user_id)
    receipt_email = (body.email or user["email"]).strip()

    try:
        result = await site_payment_providers.create_yookassa_checkout(
            site_user_id=site_user_id,
            plan_key=body.plan_key,
            tariff=tariff,
            receipt_email=receipt_email,
            return_url=body.return_url.strip(),
            extend=body.extend,
            extend_device_id=body.device_id if body.extend else None,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("checkout_yookassa: %s", e)
        raise HTTPException(status_code=500, detail="Payment provider error") from e

    ok = await site_checkout.insert_checkout_pending(
        result["invoice_id"],
        "yookassa",
        site_user_id,
        body.plan_key,
        extend_subscription=body.extend,
        extend_device_id=body.device_id if body.extend else None,
    )
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to save checkout session")

    return models_site.SiteCheckoutResponse(
        payment_id=result["invoice_id"],
        payment_url=result["payment_url"],
        amount=result["amount"],
        currency=result["currency"],
        plan_key=body.plan_key,
        duration_days=tariff["duration_days"],
    )


@router.post("/payment/checkout/cryptobot", response_model=models_site.SiteCheckoutResponse)
async def checkout_cryptobot(
    body: models_site.SiteCheckoutBody,
    site_user_id: int = Depends(get_site_user_id),
    _: None = Depends(require_api_key),
):
    await _checkout_common(site_user_id, body, "cryptobot")
    tariff = await site_tariffs_database.get_site_tariff(body.plan_key)
    if not tariff:
        raise HTTPException(status_code=404, detail="Unknown plan")
    if float(tariff.get("amount_usdt") or 0) <= 0:
        raise HTTPException(status_code=400, detail="Plan is not payable via CryptoBot")

    try:
        result = await site_payment_providers.create_cryptobot_checkout(
            site_user_id=site_user_id,
            plan_key=body.plan_key,
            tariff=tariff,
            return_url=body.return_url.strip(),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("checkout_cryptobot: %s", e)
        raise HTTPException(status_code=500, detail="Payment provider error") from e

    ok = await site_checkout.insert_checkout_pending(
        result["invoice_id"],
        "cryptobot",
        site_user_id,
        body.plan_key,
        extend_subscription=body.extend,
        extend_device_id=body.device_id if body.extend else None,
    )
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to save checkout session")

    return models_site.SiteCheckoutResponse(
        payment_id=result["invoice_id"],
        payment_url=result["payment_url"],
        amount=result["amount"],
        currency=result["currency"],
        plan_key=body.plan_key,
        duration_days=tariff["duration_days"],
    )


@router.post("/payment/checkout/oxprocessing", response_model=models_site.SiteCheckoutResponse)
async def checkout_oxprocessing(
    body: models_site.SiteCheckoutBody,
    site_user_id: int = Depends(get_site_user_id),
    _: None = Depends(require_api_key),
):
    tariff = await site_tariffs_database.get_site_tariff(body.plan_key)
    if not tariff:
        raise HTTPException(status_code=404, detail="Unknown plan")
    if float(tariff.get("amount_usdt") or 0) <= 0:
        raise HTTPException(status_code=400, detail="Plan is not payable via 0xProcessing")
    user = await user_site_database.get_user_by_id(site_user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    email = (body.email or user["email"] or None)
    if email and not user_site_database.is_valid_email(email):
        email = None

    try:
        result = site_payment_providers.create_oxprocessing_checkout(
            site_user_id=site_user_id,
            plan_key=body.plan_key,
            tariff=tariff,
            return_url=body.return_url.strip(),
            email=email,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("checkout_oxprocessing: %s", e)
        raise HTTPException(status_code=500, detail="Payment provider error") from e

    ok = await site_checkout.insert_checkout_pending(
        result["invoice_id"],
        "oxprocessing",
        site_user_id,
        body.plan_key,
        extend_subscription=body.extend,
        extend_device_id=body.device_id if body.extend else None,
    )
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to save checkout session")

    return models_site.SiteCheckoutResponse(
        payment_id=result["invoice_id"],
        payment_url=result["payment_url"],
        amount=result["amount"],
        currency=result["currency"],
        plan_key=body.plan_key,
        duration_days=tariff["duration_days"],
    )


@router.post("/webhook/yookassa")
async def webhook_yookassa(request: Request):
    from yookassa.domain.notification import WebhookNotificationFactory

    if os.getenv("YOOKASSA_SKIP_IP_CHECK", "").lower() not in ("1", "true", "yes"):
        ip = _client_ip(request)
        if not _yookassa_ip_allowed(ip):
            logger.warning("yookassa webhook rejected ip=%s", ip)
            raise HTTPException(status_code=403, detail="Forbidden")

    try:
        event_json = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    try:
        notification = WebhookNotificationFactory().create(event_json)
    except Exception as e:
        logger.exception("yookassa webhook parse: %s", e)
        raise HTTPException(status_code=400, detail="Invalid notification")

    if notification.event != "payment.succeeded":
        return {"status": "ok"}

    payment = notification.object
    metadata = payment.metadata or {}
    if metadata.get("type") != site_payment_providers.METADATA_TYPE_SITE:
        return {"status": "ok"}

    try:
        site_user_id = int(metadata.get("site_user_id") or 0)
        plan_key = str(metadata.get("plan_key") or "")
        invoice_id = str(metadata.get("invoice_id") or "")
    except (TypeError, ValueError):
        site_user_id = 0
        plan_key = ""
        invoice_id = ""

    if not site_user_id or not plan_key:
        logger.error("yookassa webhook: bad metadata %s", metadata)
        raise HTTPException(status_code=400, detail="Bad metadata")

    pending = await site_checkout.get_checkout_pending(invoice_id) if invoice_id else None
    if pending:
        extend = bool(pending.get("extend_subscription"))
        extend_device_id = pending.get("extend_device_id")
    else:
        extend = str(metadata.get("extend") or "").lower() in ("1", "true", "yes")
        raw_d = metadata.get("device_id")
        extend_device_id = None
        if raw_d not in (None, ""):
            try:
                extend_device_id = int(raw_d)
            except (TypeError, ValueError):
                extend_device_id = None
        if extend and not extend_device_id:
            logger.error("yookassa webhook: extend without device_id metadata=%s", metadata)
            raise HTTPException(status_code=400, detail="Bad metadata")

    external_id = str(payment.id)
    ok = await site_payment_fulfill.complete_site_purchase_from_webhook(
        external_id=external_id,
        site_user_id=site_user_id,
        plan_key=plan_key,
        payment_type="yookassa",
        extend=extend,
        extend_device_id=extend_device_id,
    )
    if not ok:
        raise HTTPException(status_code=500, detail="Fulfillment failed")
    if invoice_id:
        await site_checkout.delete_checkout_pending(invoice_id)
    return {"status": "ok"}


@router.post("/webhook/cryptobot")
async def webhook_cryptobot(
    request: Request,
    crypto_pay_api_signature: Optional[str] = Header(None, alias="Crypto-Pay-API-Signature"),
):
    token = os.getenv("CRYPTOBOT_TOKEN")
    if not token:
        raise HTTPException(status_code=503, detail="CryptoBot not configured")

    try:
        json_data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    if json_data.get("update_type") != "invoice_paid":
        return {"ok": True}

    if not crypto_pay_api_signature:
        raise HTTPException(status_code=401, detail="Missing signature")

    secret = hashlib.sha256(token.encode("utf-8")).digest()
    check_string = json.dumps(json_data, separators=(",", ":"), ensure_ascii=False)
    computed = hmac.new(secret, check_string.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(computed, crypto_pay_api_signature or ""):
        logger.warning("cryptobot webhook bad signature")
        raise HTTPException(status_code=401, detail="Invalid signature")

    payload_data = json_data.get("payload") or {}
    if not payload_data:
        logger.error("cryptobot webhook no payload")
        return {"ok": True}

    try:
        invoice_id = str(payload_data["invoice_id"])
        payload_raw = payload_data.get("payload") or ""
    except (KeyError, TypeError):
        logger.error("cryptobot webhook bad payload_data")
        return {"ok": True}

    pending = await site_checkout.get_checkout_pending(invoice_id)
    if pending:
        site_user_id = int(pending["site_user_id"])
        plan_key = str(pending["plan_key"])
        extend = bool(pending.get("extend_subscription"))
        extend_device_id = pending.get("extend_device_id")
    else:
        parts = str(payload_raw).split("|", 1)
        if len(parts) != 2:
            logger.error("cryptobot webhook bad payload format")
            return {"ok": True}
        try:
            site_user_id = int(parts[0])
            plan_key = parts[1]
        except ValueError:
            logger.error("cryptobot webhook parse payload")
            return {"ok": True}
        extend = False
        extend_device_id = None

    ok = await site_payment_fulfill.complete_site_purchase_from_webhook(
        external_id=invoice_id,
        site_user_id=site_user_id,
        plan_key=plan_key,
        payment_type="cryptobot",
        extend=extend,
        extend_device_id=extend_device_id,
    )
    if not ok:
        raise HTTPException(status_code=500, detail="Fulfillment failed")
    await site_checkout.delete_checkout_pending(invoice_id)
    return {"ok": True}


@router.post("/webhook/oxprocessing")
async def webhook_oxprocessing(request: Request):
    webhook_pass = os.getenv("OXP_WEBHOOK_PASS")
    if not webhook_pass:
        raise HTTPException(status_code=503, detail="OXP not configured")

    try:
        json_data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    if json_data.get("Status") != "Success":
        return {"ok": True}

    try:
        payment_id = str(json_data["PaymentId"])
        merchant_id = str(json_data["MerchantId"])
        email = str(json_data.get("Email") or "")
        currency = str(json_data.get("Currency") or "")
        billing_id = str(json_data["BillingID"])
        sig = str(json_data.get("Signature") or "")
    except (KeyError, TypeError):
        logger.error("oxp webhook missing fields")
        raise HTTPException(status_code=400, detail="Bad body")

    sign_string = f"{payment_id}:{merchant_id}:{email}:{currency}:{webhook_pass}"
    computed = hashlib.md5(sign_string.encode("utf-8")).hexdigest()
    if computed.lower() != sig.lower():
        logger.warning("oxp webhook bad signature")
        raise HTTPException(status_code=401, detail="Invalid signature")

    ok = await site_payment_fulfill.complete_site_purchase_oxp(external_id=payment_id, invoice_id=billing_id)
    if not ok:
        raise HTTPException(status_code=500, detail="Fulfillment failed")
    return {"ok": True}
