import logging

from lekivpn.core import config, db
from lekivpn.schemas import telegram as models

logger = logging.getLogger(__name__)


async def add_user(user: models.UserRegisterRequest):
    if not db.pool:
        logger.warning("Pool not initialized")
        return None

    if await is_exist_user(user.telegram_id):
        return None

    try:
        async with db.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    f"INSERT INTO {config.USERS_TABLE} (telegram_id, telegram_name, referred_by_id, is_used_bonus) VALUES (%s, %s, %s, %s)",
                    (user.telegram_id, user.telegram_name, user.referred_by_id, "false"),
                )

        return None

    except Exception as e:
        logger.exception("Ошибка при добавлении пользователя: %s", e)
        return False


async def get_user_by_telegram_id(telegram_id):
    if not db.pool:
        logger.warning("Pool not initialized")
        return

    try:
        async with db.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(f"SELECT * FROM {config.USERS_TABLE} WHERE telegram_id = %s", (telegram_id,))
                user = await cursor.fetchone()
                return user
    except Exception as e:
        logger.exception("Ошибка при получении пользователя: %s", e)
        return None


async def save_user_bonus_by_telegram_id(telegram_id):
    if not db.pool:
        logger.warning("Pool not initialized")
        return None

    try:
        async with db.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    f"UPDATE {config.USERS_TABLE} SET is_used_bonus = %s WHERE telegram_id = %s",
                    ("true", telegram_id),
                )

                if cursor.rowcount == 0:
                    print(f"⚠️ Пользователь с telegram_id {telegram_id} не найден")
                    return None

                print(f"✅ Бонус использован для пользователя {telegram_id}")
                return True

    except Exception as e:
        logger.exception("Ошибка при обновлении бонуса: %s", e)
        return None


async def get_user_bonus_status(telegram_id):
    if not db.pool:
        logger.warning("Pool not initialized")
        return None

    try:
        async with db.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(f"SELECT is_used_bonus FROM {config.USERS_TABLE} WHERE telegram_id = %s", (telegram_id,))
                result = await cursor.fetchone()

                if not result:
                    print(f"⚠️ Пользователь {telegram_id} не найден")
                    return None

                bonus_value = result["is_used_bonus"] if isinstance(result, dict) else result[0]

                if isinstance(bonus_value, str):
                    return bonus_value.lower() == "true"
                else:
                    return bool(bonus_value)

    except Exception as e:
        logger.exception("Ошибка при получении статуса бонуса: %s", e)
        return None


async def get_user_referred_id(telegram_id):
    if not await is_exist_user(telegram_id):
        return None

    try:
        async with db.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(f"SELECT referred_by_id FROM {config.USERS_TABLE} WHERE telegram_id = %s", (telegram_id,))
                result = await cursor.fetchone()

                if not result:
                    return None

                return result["referred_by_id"] if isinstance(result, dict) else result[0]

    except Exception as e:
        logger.exception("Ошибка при получении referred_by_id: %s", e)
        return None


async def remove_referr_by_telegram_id(telegram_id):
    if not db.pool:
        logger.warning("Pool not initialized")
        return None

    try:
        async with db.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    f"UPDATE {config.USERS_TABLE} SET referred_by_id = %s WHERE telegram_id = %s",
                    (None, telegram_id),
                )

                if cursor.rowcount == 0:
                    print(f"⚠️ Пользователь с telegram_id {telegram_id} не найден")
                    return None

                print(f"✅ Рефералл удалён для {telegram_id}")
                return True

    except Exception as e:
        logger.exception("Ошибка удаления рефералла: %s", e)
        return None


async def is_exist_user(telegram_id):
    async with db.pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(f"SELECT * FROM {config.USERS_TABLE} WHERE telegram_id = %s", (telegram_id,))
            user = await cursor.fetchone()
            return bool(user)


async def log_payment(payload: models.PaymentLogRequest):
    if not db.pool:
        return None
    try:
        async with db.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    f"INSERT INTO {config.PAYMENTS_TABLE} (telegram_id, amount_kopecks, currency, product_id, device_id, payment_type) VALUES (%s, %s, %s, %s, %s, %s)",
                    (
                        payload.telegram_id,
                        payload.amount_kopecks,
                        payload.currency,
                        payload.product_id,
                        payload.device_id,
                        payload.payment_type,
                    ),
                )
        return True
    except Exception as e:
        logger.exception("Ошибка записи лога оплаты: %s", e)
        return None
