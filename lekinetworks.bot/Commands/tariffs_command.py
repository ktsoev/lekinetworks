from aiogram import types, Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

import network_helper
import models
import config
from datetime import date, datetime

async def show_panel(message: types.Message):
    user = models.User(telegram_id=str(message.from_user.id))

    devices = await network_helper.post(config.SERVER_URL + config.GET_USER_ORDERS_ENDPOINT, user.model_dump())

    has_devices = bool(devices)

    # Единый экран управления подпиской (без кнопки пробного периода —
    # он доступен дальше в тарифах/оплате)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="➕ Купить подписку",
                callback_data="buy_vpn",
            ),
            InlineKeyboardButton(
                text="🔁 Продлить",
                callback_data="extend_vpn",
            ),
        ],
        [
            InlineKeyboardButton(
                text="📱 Мои устройства",
                callback_data="show_devices",
            ),
        ],
    ])

    if has_devices:
        text = (
            "🚀 *VPN подписка*\n\n"
            "У вас уже есть активная подписка.\n"
            "Вы можете продлить её или купить для нового устройства.\n\n"
            "Также здесь можно активировать пробный период для нового устройства."
        )
    else:
        text = (
            "🚀 *VPN подписка*\n\n"
            "У вас пока нет активной подписки.\n\n"
            "Выберите, с чего начать:\n"
            "• активировать пробный период\n"
            "• сразу купить подписку\n"
            "• позже вернуться к этому меню через «VPN подписка»"
        )

    await message.answer(text, reply_markup=keyboard, parse_mode="Markdown")

async def handle_buy_vpn(callback: types.CallbackQuery, bot: Bot):
    user = models.User(telegram_id=str(callback.from_user.id))

    new_device_id = await network_helper.post(config.SERVER_URL + config.GET_USER_NEW_DEVICE_ID_ENDPOINT, user.model_dump())

    if not new_device_id:
        await bot.send_message(callback.from_user.id,
            f"Произошла ошибка, перезапустите бота через /start При повторных ошибках обратитесть в {config.SUPPORT_USERNAME}\n"
            f"Укажите ваш id при обращении: {callback.from_user.id}"
            )
        return
    
    await show_tariffs_panel(callback, bot, new_device_id)
    
#extend
async def handle_show_extend_devices(callback: types.CallbackQuery, bot: Bot):
    user = models.User(telegram_id=str(callback.from_user.id))

    user_devices = await network_helper.post(config.SERVER_URL + config.GET_USER_ORDERS_ENDPOINT, user.model_dump())

    if not user_devices:
        await bot.send_message(callback.from_user.id,
            f"У вас нет созданных устройств"
        )
        return

    keyboard = []

    keyboard = [
        [InlineKeyboardButton(
            text=f"Устройство {user_device}", 
            callback_data=f"extend_device/{user_device}"
        )] for user_device in user_devices
    ]

    await bot.send_message(callback.from_user.id,
        f"Выберите устройство для продления подписки",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )

async def handle_extend_vpn(callback: types.CallbackQuery, bot: Bot):
    parts = callback.data.split("/")
    await show_tariffs_panel(callback, bot, parts[-1])
#extend

#show deivces
async def handle_show_devices(callback: types.CallbackQuery, bot: Bot):
    user = models.User(telegram_id=str(callback.from_user.id))

    user_devices = await network_helper.post(config.SERVER_URL + config.GET_USER_ORDERS_ENDPOINT, user.model_dump())

    expiry_dates = []
    for user_device in user_devices:
        expiry_request = models.VpnRequest(telegram_id=str(callback.from_user.id), device_id=int(user_device))
        expiry_date = await network_helper.post(config.SERVER_URL + config.GET_VPN_EXPIRY_DATE_ENDPOINT, expiry_request.model_dump())
        expiry_dates.append(expiry_date)

    if not user_devices:
        await bot.send_message(callback.from_user.id,
            f"У вас нет созданных устройств"
        )
        return

    keyboard = []

    keyboard = [
        [InlineKeyboardButton(
            text=f"Устройство {user_device} {get_expiry_date(expiry_dates, user_devices, user_device)}", 
            callback_data=f"show_device/{user_device}"
        )] 
        for user_device in user_devices
    ]

    await bot.send_message(callback.from_user.id,
        f"Выберите устройство для подключения",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )

async def handle_show_device(callback: types.CallbackQuery, bot: Bot):
    parts = callback.data.split("/")

    vpn_request = models.VpnRequest(telegram_id=str(callback.from_user.id), device_id=int(parts[-1]))

    vpn_key = await network_helper.post(config.SERVER_URL + config.GET_VPN_KEY_ENDPOINT, vpn_request.model_dump())

    if not vpn_key:
        await bot.send_message(callback.from_user.id,
            f"Ошибка получения ссылки на подключение"
        )
        return

    await bot.send_message(callback.from_user.id,
        f"Нажмите на ссылку ниже, чтобы открыть инструкцию для подключения\n\n"
        f"{vpn_key}"
    )
#show deivces

async def show_tariffs_panel_by_message(message: types.Message, device_id):
    await message.answer(
        "🚀 *VPN подписка*\n\n"
        "Выберите тариф ниже.\n"
        "Если хотите сначала проверить — активируйте пробный период.\n",
        reply_markup=get_tariffs_buttons(device_id, include_trial=True),
        parse_mode="Markdown"
    )

async def show_tariffs_panel(callback: types.CallbackQuery, bot: Bot, device_id):
    await bot.send_message(
        callback.from_user.id,
        "🚀 *VPN подписка*\n\n"
        "Выберите тариф ниже.\n"
        "Если хотите сначала проверить — активируйте пробный период.\n",
        reply_markup=get_tariffs_buttons(device_id, include_trial=True), ########
        parse_mode="Markdown"
    )

def get_tariffs_buttons(device_id=1, include_trial: bool = False):
    rows = []
    if include_trial:
        rows.append([
            InlineKeyboardButton(
                text="🔥 Пробный период (3 дня)",
                callback_data="3_days_test",
            )
        ])

    rows.extend([
        [InlineKeyboardButton(
            text=f"1 Месяц - {int(config.PRODUCTS.get('1_month')['price']/100)}₽", 
            callback_data=f"1_month/{device_id}"
        )],
        [InlineKeyboardButton(
            text=f"3 Месяца - {int(config.PRODUCTS.get('3_month')['price']/100)}₽", 
            callback_data=f"3_month/{device_id}"
        )],
        [InlineKeyboardButton(
            text=f"6 Месяцев - {int(config.PRODUCTS.get('6_month')['price']/100)}₽", 
            callback_data=f"6_month/{device_id}"
        )],
        [InlineKeyboardButton(
            text=f"🔥 Выгодно / 12 месяцев - {int(config.PRODUCTS.get('12_month')['price']/100)}₽", 
            callback_data=f"12_month/{device_id}"
        )],
    ])

    keyboard = InlineKeyboardMarkup(inline_keyboard=rows)

    return keyboard

def get_expiry_date(expiry_dates, user_devices, user_device):
    if expiry_dates[user_devices.index(user_device)]:
        return f"({expiry_dates[user_devices.index(user_device)]})"
    else:
        return ""