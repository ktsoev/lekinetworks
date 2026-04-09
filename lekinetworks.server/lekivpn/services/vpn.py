from datetime import datetime, timedelta

from remnawave import RemnawaveSDK
from remnawave.models import (
    CreateUserRequestDto,
    GetAllInternalSquadsResponseDto,
    InternalSquadDto,
    TelegramUserResponseDto,
    UpdateUserRequestDto,
    UserResponseDto,
)

from lekivpn.schemas import telegram as models
from lekivpn.services import servers_database


async def add_user_async(api: RemnawaveSDK, vpnOrderRequest: models.VpnOrderRequest, device_id) -> str:
    try:
        username = get_username(vpnOrderRequest.telegram_id, device_id)

        exist_user = await is_exist_user(api, username)

        if exist_user:
            return None

        expire_timestamp: datetime = datetime.now() + timedelta(days=vpnOrderRequest.duration_days + 1)

        free_squad_uuid = await get_free_squad_uuid(api)

        await api.users.create_user(
            CreateUserRequestDto(
                username=username,
                telegram_id=vpnOrderRequest.telegram_id,
                expire_at=expire_timestamp,
                hwid_device_limit=4,
                active_internal_squads=[free_squad_uuid],
            )
        )

        user: UserResponseDto = await api.users.get_user_by_username(username)
        return user.subscription_url

    except Exception as e:
        print(f"Vpn handler add user exception: {e}")
        return None


async def delete_user_async(api: RemnawaveSDK, username) -> bool:
    try:
        user = await api.users.get_user_by_username(username)

        if not user:
            return False

        await api.users.delete_user(str(user.uuid))
        return True
    except Exception:
        return False


async def extend_user_async(api: RemnawaveSDK, username, days) -> str:
    try:
        user: UserResponseDto = await api.users.get_user_by_username(username)
        if not user:
            return False

        current_expire = user.expire_at

        if current_expire:
            new_expire: datetime = current_expire + timedelta(days=days)
        else:
            new_expire: datetime = datetime.now() + timedelta(days=days)

        updated_user = UpdateUserRequestDto(uuid=user.uuid, expire_at=new_expire)
        await api.users.update_user(updated_user)

        print(f"✅ {username} продлён на {days} дней")
        return True

    except Exception as e:
        print(f"❌ Ошибка продления {username}: {e}")
        return False


async def get_subscription_async(api: RemnawaveSDK, username) -> str:
    try:
        user = await is_exist_user(api, username)

        if not user:
            return False

        user_info = await api.users.get_user_by_username(username)
        return user_info.subscription_url
    except Exception:
        return False


async def is_exist_user(api: RemnawaveSDK, username) -> bool:
    try:
        user_info = await api.users.get_user_by_username(username)
        return user_info
    except Exception as e:
        return False


async def get_last_device_id(api: RemnawaveSDK, telegram_id) -> int:
    try:
        user_orders: TelegramUserResponseDto = await get_all_user_orders(api, telegram_id)
        if not user_orders:
            return 1

        device_ids = []

        for user_order in user_orders:
            parts = user_order.username.split("_")
            device_part = parts[-1]

            try:
                device_id = int(device_part)
                if device_id > 0:
                    device_ids.append(device_id)
            except Exception:
                pass

        if not device_ids:
            return 1

        device_ids.sort()

        expected = 1
        for d in device_ids:
            if d != expected:
                return expected
            expected += 1

        return expected

    except Exception as e:
        print(f"❌ Ошибка при получении последнего device_id: {e}")
        return 1


async def get_all_user_orders(api: RemnawaveSDK, telegram_id) -> TelegramUserResponseDto:
    try:
        user_orders: TelegramUserResponseDto = await api.users.get_users_by_telegram_id(telegram_id)

        return user_orders
    except Exception as e:
        print(f"❌ Ошибка получения заказов юзера {telegram_id}: {e}")
        return None


async def get_all_active_orders(api: RemnawaveSDK, telegram_id):
    try:
        users: TelegramUserResponseDto = await api.users.get_users_by_telegram_id(telegram_id)

        result = []

        for user_data in users:
            if user_data.username.startswith(f"{telegram_id}_") and user_data.status == "ACTIVE":
                parts = user_data.username.split("_")
                result.append(parts[-1])

        result.sort()
        return result
    except Exception as e:
        print(f"❌ Ошибка получения заказов юзера {telegram_id}: {e}")
        return None


async def get_device_expiry_date(api: RemnawaveSDK, username):
    try:
        user = await api.users.get_user_by_username(username)

        if not user:
            print(f"❌ Пользователь {username} не найден")
            return None

        expiry = user.expire_at

        if not expiry:
            print(f"⚠ У пользователя {username} нет даты истечения")
            return None

        expiry_date = expiry.strftime("%d-%m-%Y")
        return expiry_date

    except Exception as e:
        print(f"❌ Ошибка получения expiry для {username}: {e}")
        return None


async def get_free_squad_uuid(api: RemnawaveSDK):
    squads: GetAllInternalSquadsResponseDto = await api.internal_squads.get_internal_squads()

    last_squad_uuid = ""
    for squad in squads.internal_squads:
        max_users: int = await servers_database.get_users_count_by_uuid(str(squad.uuid))
        last_squad_uuid = squad.uuid

        if squad.info.members_count < max_users:
            return squad.uuid

    return last_squad_uuid


def get_username(telegram_id, device_id):
    return f"{telegram_id}_{device_id}"
