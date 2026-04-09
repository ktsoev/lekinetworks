import logging
from typing import Optional

from remnawave import RemnawaveSDK

from lekivpn.schemas import telegram as models
from lekivpn.services import servers_database, user_database, vpn

logger = logging.getLogger(__name__)

api = None  # type: RemnawaveSDK | None


def set_api(api_vpn: RemnawaveSDK):
    global api
    api = api_vpn


async def add_vpn_order(vpnOrderRequest: models.VpnOrderRequest) -> Optional[str]:
    try:
        if not await user_database.is_exist_user(vpnOrderRequest.telegram_id):
            logger.warning("Юзер не найден: %s", vpnOrderRequest.telegram_id)
            return None

        device_id = await vpn.get_last_device_id(api, vpnOrderRequest.telegram_id)

        vpn_url = await vpn.add_user_async(api, vpnOrderRequest, device_id)

        if not vpn_url:
            logger.warning("Ключ не создан для telegram_id=%s", vpnOrderRequest.telegram_id)
            return None

        return vpn_url
    except Exception as e:
        logger.exception("Ошибка при покупке VPN: %s", e)


async def remove_vpn_order(user: models.VpnRequest):
    try:
        if not await is_exist_order(user):
            return False

        username = vpn.get_username(user.telegram_id, user.device_id)
        if not await vpn.delete_user_async(api, username):
            return False

        return True
    except Exception as e:
        logger.exception("Ошибка при удалении VPN: %s", e)


async def extend_vpn_order(user: models.VpnExtendRequest):
    try:
        vpnRequest: models.VpnRequest = models.VpnRequest(telegram_id=user.telegram_id, device_id=user.device_id)
        if not await is_exist_order(vpnRequest):
            return False

        username = vpn.get_username(user.telegram_id, user.device_id)
        status = await vpn.extend_user_async(api, username, user.duration_days + 1)

        if not status:
            return False

        return True
    except Exception as e:
        logger.exception("Ошибка при продлении VPN заказа: %s", e)
        return False


async def get_vpn_key(user: models.VpnRequest):
    try:
        if not await user_database.is_exist_user(user.telegram_id) or not await is_exist_order(user):
            return False

        username = vpn.get_username(user.telegram_id, user.device_id)
        vpn_key = await vpn.get_subscription_async(api, username)

        if not vpn_key:
            return False

        return vpn_key
    except Exception as e:
        logger.exception("Ошибка при получении ключа VPN: %s", e)


async def get_order_expiry_date(request: models.VpnRequest) -> Optional[str]:
    try:
        if not await user_database.is_exist_user(request.telegram_id):
            return None

        expiry_date = await vpn.get_device_expiry_date(
            api, vpn.get_username(request.telegram_id, request.device_id)
        )
        return expiry_date
    except Exception as e:
        logger.exception("Ошибка получения даты истечения: %s", e)
        return None


async def get_active_devices(telegram_id: str):
    try:
        user_devices = await vpn.get_all_active_orders(api, telegram_id)

        return user_devices
    except Exception as e:
        logger.exception("Ошибка получения активных устройств: %s", e)
        return False


async def get_new_device_id(telegram_id: str):
    try:
        device_id = await vpn.get_last_device_id(api, telegram_id)

        return device_id
    except Exception as e:
        logger.exception("Ошибка получения device_id: %s", e)
        return False


async def add_referral_bonus(user: models.User):
    try:
        if not await user_database.is_exist_user(user.telegram_id):
            logger.warning("Юзер не найден для реферального бонуса: %s", user.telegram_id)
            return False

        referred_id = await user_database.get_user_referred_id(user.telegram_id)

        if not referred_id:
            logger.warning("Нет реферала для telegram_id=%s", user.telegram_id)
            return False

        vpn_request = models.VpnRequest(telegram_id=referred_id, device_id=1)
        vpn_key = await get_vpn_key(vpn_request)

        if not vpn_key:
            vpn_order_request = models.VpnOrderRequest(telegram_id=referred_id, duration_days=7)
            await add_vpn_order(vpn_order_request)
        else:
            vpn_extend_request = models.VpnExtendRequest(telegram_id=referred_id, duration_days=7, device_id=1)
            await extend_vpn_order(vpn_extend_request)

        expiry_date = await get_order_expiry_date(vpn_request)
        referred_data = models.ReferredData(referred_id=str(referred_id), expiry_date=str(expiry_date))

        await user_database.remove_referr_by_telegram_id(user.telegram_id)

        return referred_data.model_dump()
    except Exception as e:
        logger.exception("Ошибка начисления реферального бонуса: %s", e)
        return False


async def get_user_referred_id(user: models.User):
    try:
        referred_id = await user_database.get_user_referred_id(user.telegram_id)

        if not referred_id:
            return False

        return referred_id
    except Exception as e:
        logger.exception("Ошибка получения реферального id: %s", e)
        return False


async def is_exist_order(user: models.VpnRequest) -> Optional[bool]:
    try:
        username = vpn.get_username(user.telegram_id, user.device_id)
        status = await vpn.is_exist_user(api, username)

        return status
    except Exception as e:
        logger.exception("Ошибка при проверке существующего заказа: %s", e)


async def activate_promocode(promocodeData: models.PromocodeData):
    try:
        response = await servers_database.activate_promocode(promocodeData)

        if not response:
            return None

        return response.model_dump()
    except Exception as e:
        logger.exception("Ошибка активации промокода: %s", e)
