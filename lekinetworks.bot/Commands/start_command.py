from aiogram import types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

import models
import network_helper
import config

async def show_message(message: types.Message):
    text = (
        "🌿 *LEKI Networks*\n\n"
        "Быстрый и надёжный VPN для безопасного доступа в интернет.\n\n"
        "Почему выбирают нас:\n"
        "🎁 +7 дней за каждого приглашённого друга\n"
        "🛡 Работает даже при блокировках\n"
        "🔒 Приватность и защита данных\n"
        "🌍 Доступ к мировому контенту\n"
        "💬 Поддержка 24/7"
    )

    await message.answer(text, reply_markup=config.DEFAULT_KEYBOARD, parse_mode="Markdown")

    print(f"Аргументы: {message.text.split()}")
    
    referrer_id = None
    if len(message.text.split()) > 1:
        try:
            referrer_id = str(message.text.split()[1])
            print(f"Найден referrer_id: {referrer_id}")
            
            if referrer_id == str(message.from_user.id):
                referrer_id = None
        except ValueError as e:
            print(f"Ошибка: {e}")
            pass

    user_data = models.UserRegisterRequest(
        telegram_id=str(message.from_user.id),
        telegram_name=str(message.from_user.full_name),
        referred_by_id=referrer_id)
    
    is_new_user = await network_helper.post(config.SERVER_URL + config.ADD_USER_ENDPOINT, user_data.model_dump())