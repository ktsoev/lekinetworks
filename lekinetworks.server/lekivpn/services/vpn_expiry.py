import asyncio
from datetime import datetime, timezone

from remnawave.models import GetAllUsersResponseDto

from lekivpn.core import config
from lekivpn.services import server as server_mod, vpn


async def start_vpn_cleaner():
    while True:
        try:
            await check_and_remove_expired_vpns()
            await asyncio.sleep(config.VPN_EXPIRY_CHECK_DURATION)
        except Exception as e:
            print(f"❌ Ошибка в очистке: {e}")
            await asyncio.sleep(config.HOUR_IN_SECONDS)


async def check_and_remove_expired_vpns():
    try:
        print(f"🔍 Проверка истёкших VPN: {datetime.now()}")

        api = server_mod.api
        users: GetAllUsersResponseDto = await api.users.get_all_users()

        vpn_remove_count = 0

        for user in users.users:
            expiry_time = user.expire_at.replace(tzinfo=timezone.utc)
            now_date: datetime = datetime.now(timezone.utc)

            if expiry_time < now_date:
                await vpn.delete_user_async(api, user.username)
                vpn_remove_count += 1

        print(f"✅ Удалено истёкших VPN: {vpn_remove_count}")

    except Exception as e:
        print(f"❌ Ошибка проверки VPN: {e}")
