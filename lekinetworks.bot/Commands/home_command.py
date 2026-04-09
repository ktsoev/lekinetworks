from aiogram import types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

async def execute(message: types.Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="📱 Мои устройства",
                callback_data="show_devices",
            ),
            InlineKeyboardButton(
                text="🔁 Продлить",
                callback_data="extend_vpn",
            ),
        ],
        [
            InlineKeyboardButton(
                text="🎁 Рефералы",
                callback_data="show_referral_message",
            ),
            InlineKeyboardButton(
                text="💬 Поддержка",
                callback_data="show_support_message",
            ),
        ],
        [
            InlineKeyboardButton(
                text="🎟 Промокод",
                callback_data="activate_promocode",
            ),
        ],
    ])

    text = (
        "👤 *Личный кабинет LEKI Networks*\n\n"
        "Управляйте устройствами и подпиской, активируйте промокоды и приглашайте друзей."
    )

    await message.answer(text, reply_markup=keyboard, parse_mode="Markdown")