from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

SUPPORT_USERNAME = "@support"

SERVER_URL = "http://127.0.0.1:8000/" #LOCAL TEST
#SERVER_URL = "http://192.168.0.21:8000/"

ADD_USER_ENDPOINT = "add-user"
SAVE_USER_BONUS_ENDPOINT = "save-user-bonus"
GET_USER_BONUS_ENDPOINT = "get-user-bonus-status"

ADD_VPN_ORDER = "add-vpn-order"
GET_USER_ORDERS_ENDPOINT = "get-user-orders"
GET_USER_NEW_DEVICE_ID_ENDPOINT = "get-user-new-device-id"
GET_USER_ORDERS_ENDPOINT = "get-user-orders"
GET_VPN_KEY_ENDPOINT = "get-vpn-key"
EXTEND_VPN_ORDER_ENDPOINT = "extend-vpn-order"
GET_VPN_EXPIRY_DATE_ENDPOINT = "get-vpn-expiry-date"
GET_USER_REFERRED_ID_ENDPOINT = "get-user-referred-id"
ADD_REFERRAL_BONUS_ENDPOINT = "add-referral-bonus"
ACTIVATE_PROMOCODE_ENDPOINT = "activate-promocode"
LOG_PAYMENT_ENDPOINT = "log-payment"

DATE_TIME_FORMAT = "%d.%m.%Y"

Bot_Commands = {
    "info" : "ℹ️ О сервисе",
    "buy" : "🚀 VPN подписка",
    "home" : "👤 Личный кабинет"
}

DEFAULT_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text=Bot_Commands["buy"])],
        [KeyboardButton(text=Bot_Commands["home"]), KeyboardButton(text=Bot_Commands["info"])],
    ],
    resize_keyboard=True,
)

PRODUCTS = {
    "1_month": {
        "name": "⭐ 1 Месяц - 129₽",
        "description": "🔒 Доступ к VPN на 30 дней",
        "price": 12900, #14900
        "duration_days": 30
    },
    "3_month": {
        "name": "⭐ 3 Месяца - 349₽", 
        "description": "🔒 Доступ к VPN на 90 дней",
        "price": 34900, #39900
        "duration_days": 90
    },
    "6_month": {
        "name": "⭐ 6 Месяцев - 649₽", 
        "description": "🔒 Доступ к VPN на 180 дней",
        "price": 64900, #89900
        "duration_days": 180
    },
    "12_month": {
        "name": "🔥 Выгодно / 12 месяцев - 1199₽",
        "description": "🔒 Доступ к VPN на 365 дней",
        "price": 119900, #159900
        "duration_days": 365
    },
    "3_days_test": {
        "name": "🔥 3 дня бесплатно",
        "description": "🔒 Доступ к VPN на 3 дня",
        "price": 0,
        "duration_days": 2
    }
}