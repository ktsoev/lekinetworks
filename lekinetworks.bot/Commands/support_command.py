from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

async def execute(bot: Bot, callback: types.CallbackQuery):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🛟 Написать", 
            url="https://t.me/LeKiVPNsupport"
        )],
    ])

    await callback.bot.send_message(
        callback.from_user.id,
        "🛟 Поддержка\n\n"
        "Возникли вопросы или проблемы?\n"
        "Напишите в нашу поддержку — мы постараемся помочь как можно быстрее.\n\n"
        "Нажмите кнопку ниже, чтобы открыть чат.",
        reply_markup=keyboard
    )