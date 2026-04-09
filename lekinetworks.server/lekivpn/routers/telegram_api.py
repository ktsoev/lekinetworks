from fastapi import APIRouter, Depends, HTTPException, Request

from lekivpn.routers.deps import require_api_key
from lekivpn.schemas import telegram as models
from lekivpn.services import server as server_handler
from lekivpn.services import user_database

router = APIRouter()


def init(api_vpn):
    server_handler.set_api(api_vpn)


@router.post("/add-user")
async def db_add_user(request: models.UserRegisterRequest, _: None = Depends(require_api_key)):
    print(f"📥 add-user telegram_id={getattr(request, 'telegram_id', '?')}")

    identifier = request.telegram_id or request.telegram_name
    if not identifier:
        raise HTTPException(status_code=400, detail="Request data error")

    return await user_database.add_user(request)


@router.post("/save-user-bonus")
async def db_save_user_bonus(request: models.User, _: None = Depends(require_api_key)):
    print(f"📥 save-user-bonus telegram_id={getattr(request, 'telegram_id', '?')}")

    identifier = request.telegram_id
    if not identifier:
        raise HTTPException(status_code=400, detail="Request data error")

    return await user_database.save_user_bonus_by_telegram_id(request.telegram_id)


@router.post("/get-user-bonus-status")
async def db_get_user_bonus(request: models.User, _: None = Depends(require_api_key)):
    print(f"📥 get-user-bonus-status telegram_id={getattr(request, 'telegram_id', '?')}")

    identifier = request.telegram_id
    if not identifier:
        raise HTTPException(status_code=400, detail="Request data error")

    return await user_database.get_user_bonus_status(request.telegram_id)


@router.post("/add-vpn-order")
async def db_add_vpn_order(request: models.VpnOrderRequest, _: None = Depends(require_api_key)):
    print(f"📥 add-vpn-order telegram_id={getattr(request, 'telegram_id', '?')}")

    identifier = request.telegram_id or request.duration_days
    if not identifier:
        raise HTTPException(status_code=400, detail="Request data error")

    return await server_handler.add_vpn_order(request)


@router.post("/extend-vpn-order")
async def db_extend_vpn_order(request: models.VpnExtendRequest, _: None = Depends(require_api_key)):
    identifier = request.telegram_id or request.duration_days or request.device_id
    if not identifier:
        raise HTTPException(status_code=400, detail="Request data error")

    return await server_handler.extend_vpn_order(request)


@router.post("/get-vpn-key")
async def db_get_vpn_key(request: models.VpnRequest, _: None = Depends(require_api_key)):
    identifier = request.telegram_id or request.device_id
    if not identifier:
        raise HTTPException(status_code=400, detail="Request data error")

    return await server_handler.get_vpn_key(request)


@router.post("/get-user-orders")
async def db_get_user_orders(request: models.User, _: None = Depends(require_api_key)):
    if not request.telegram_id:
        raise HTTPException(status_code=400, detail="Request data error")

    return await server_handler.get_active_devices(request.telegram_id)


@router.post("/get-user-new-device-id")
async def db_get_user_new_device_id(request: models.User, _: None = Depends(require_api_key)):
    if not request.telegram_id:
        raise HTTPException(status_code=400, detail="Request data error")

    return await server_handler.get_new_device_id(request.telegram_id)


@router.post("/get-vpn-expiry-date")
async def db_get_vpn_expiry_date(request: models.VpnRequest, _: None = Depends(require_api_key)):
    identifier = request.telegram_id or request.device_id
    if not identifier:
        raise HTTPException(status_code=400, detail="Request data error")

    return await server_handler.get_order_expiry_date(request)


@router.post("/add-referral-bonus")
async def add_referral_bonus(request: models.User, _: None = Depends(require_api_key)):
    identifier = request.telegram_id
    if not identifier:
        raise HTTPException(status_code=400, detail="Request data error")

    response = await server_handler.add_referral_bonus(request)
    return response


@router.post("/activate-promocode")
async def activate_promocode(request: models.PromocodeData, _: None = Depends(require_api_key)):
    identifier = request.telegram_id or request.promocode
    if not identifier:
        raise HTTPException(status_code=400, detail="Request data error")

    response = await server_handler.activate_promocode(request)
    print(f"📥 activate-promocode telegram_id={getattr(request, 'telegram_id', '?')} result={'ok' if response else 'fail'}")
    return response


@router.post("/log-payment")
async def log_payment_endpoint(request: models.PaymentLogRequest, _: None = Depends(require_api_key)):
    if not request.telegram_id or request.amount_kopecks is None or not request.payment_type:
        raise HTTPException(status_code=400, detail="Request data error")
    await user_database.log_payment(request)
    return {}
