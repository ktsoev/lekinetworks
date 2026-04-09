from aiogram import types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

async def execute(message: types.Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="Политика конфиденциальности", 
            url="https://leki.example.com/privacy-policy"
        )],
    ])

    await message.answer(
            "🔐 Конфиденциальность\n\n"
            "Безопасность и приватность пользователей — наш приоритет.\n"
            "Вы можете ознакомиться с полной политикой обработки данных по ссылке ниже.",
            reply_markup=keyboard
        )