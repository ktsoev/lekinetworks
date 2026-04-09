import logging
from typing import Optional

from lekivpn.core import config, db
from lekivpn.schemas import telegram as models
from lekivpn.services import server as server_handler

logger = logging.getLogger(__name__)


async def get_users_count_by_uuid(uuid) -> int:
    if not db.pool:
        logger.warning("Pool not initialized")
        return 0

    try:
        async with db.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(f"SELECT squad_max_users FROM {config.SERVERS_TABLE} WHERE squad_uuid = %s", (uuid,))
                result = await cursor.fetchone()

                if not result:
                    logger.warning("Сервер с UUID %s не найден", uuid)
                    return 0

                return result["squad_max_users"] if isinstance(result, dict) else result[0]

    except Exception as e:
        logger.exception("Ошибка при получении max_users: %s", e)
        return 0


async def activate_promocode(promocodeData: models.PromocodeData) -> Optional[models.PromocodeResponse]:
    if not db.pool:
        logger.warning("Пул не инициализирован")
        return None

    try:
        async with db.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    f"SELECT * FROM {config.PROMOCODES_TABLE} WHERE promocode_word = %s",
                    (promocodeData.promocode,),
                )
                data = await cursor.fetchone()

                if not data:
                    return None

                if isinstance(data, dict):
                    number_of_uses = data["number_of_uses"]
                    max_number_of_uses = data["max_number_of_uses"]
                    bonus_days = data["bonus_days"]
                else:
                    number_of_uses = data[3]
                    max_number_of_uses = data[2]
                    bonus_days = data[4]

                if number_of_uses >= max_number_of_uses:
                    return None

                number_of_uses += 1
                await cursor.execute(
                    f"UPDATE {config.PROMOCODES_TABLE} SET number_of_uses = %s WHERE promocode_word = %s",
                    (number_of_uses, promocodeData.promocode),
                )

        vpnOrderRequest = models.VpnOrderRequest(
            telegram_id=promocodeData.telegram_id,
            duration_days=bonus_days,
        )
        vpn_response_url = await server_handler.add_vpn_order(vpnOrderRequest)

        promocodeResponse = models.PromocodeResponse(
            telegram_id=promocodeData.telegram_id,
            duration_days=bonus_days,
            vpn_url=str(vpn_response_url),
        )
        await _log_promocode_activation(promocodeData.telegram_id, promocodeData.promocode)
        return promocodeResponse

    except Exception as e:
        logger.exception("Ошибка при активации промокода: %s", e)
        return None


async def activate_promocode_site(site_user_id: int, promocode: str) -> Optional[models.PromocodeResponse]:
    from lekivpn.services import site_server
    from lekivpn.services import user_site_database

    if not db.pool:
        logger.warning("Пул не инициализирован")
        return None
    if not await user_site_database.user_exists(site_user_id):
        return None

    try:
        async with db.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    f"SELECT * FROM {config.PROMOCODES_TABLE} WHERE promocode_word = %s",
                    (promocode,),
                )
                data = await cursor.fetchone()

                if not data:
                    return None

                if isinstance(data, dict):
                    number_of_uses = data["number_of_uses"]
                    max_number_of_uses = data["max_number_of_uses"]
                    bonus_days = data["bonus_days"]
                else:
                    number_of_uses = data[3]
                    max_number_of_uses = data[2]
                    bonus_days = data[4]

                if number_of_uses >= max_number_of_uses:
                    return None

                number_of_uses += 1
                await cursor.execute(
                    f"UPDATE {config.PROMOCODES_TABLE} SET number_of_uses = %s WHERE promocode_word = %s",
                    (number_of_uses, promocode),
                )

        vpn_response_url = await site_server.add_vpn_order_site(site_user_id, bonus_days)
        if not vpn_response_url:
            return None

        tid = user_site_database.panel_telegram_id(site_user_id)
        promocode_response = models.PromocodeResponse(
            telegram_id=tid,
            duration_days=bonus_days,
            vpn_url=str(vpn_response_url),
        )
        await _log_promocode_activation(tid, promocode)
        return promocode_response

    except Exception as e:
        logger.exception("Ошибка при активации промокода (site): %s", e)
        return None


async def _log_promocode_activation(telegram_id: str, promocode_word: str):
    if not db.pool:
        return
    try:
        async with db.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    f"INSERT INTO {config.PROMOCODE_ACTIVATIONS_TABLE} (telegram_id, promocode_word) VALUES (%s, %s)",
                    (telegram_id, promocode_word),
                )
    except Exception as e:
        logger.exception("Ошибка записи лога активации промокода: %s", e)
