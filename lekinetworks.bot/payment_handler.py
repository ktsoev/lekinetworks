import json
import logging
from decouple import config as conf
from aiogram import types, Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice

import network_helper
import models
import string_formater
import config

logger = logging.getLogger(__name__)


async def create_invoice(callback: types.CallbackQuery, bot: Bot):
    callback_parts = callback.data.split("/")
    device_id = callback_parts[-1]

    product_data = config.PRODUCTS.get(callback_parts[0])
    
    if not product_data:
        await callback.answer("❌ Продукт не найден")
        return
    
    try:
        await bot.send_invoice(
            chat_id=callback.from_user.id,
            title="LEKI Networks",
            description=product_data['description'],
            payload=f"{get_product_id_by_name(product_data['name'])}/{device_id}",
            provider_token=conf('YOOKASSA_TOKEN', cast=str),
            currency="RUB",
            prices=[
                LabeledPrice(
                    label=product_data['name'],
                    amount=product_data['price']
                )
            ],
            need_phone_number=True,
            send_phone_number_to_provider=True,
            provider_data=json.dumps({
                        "receipt": {
                        "items": [
                        {
                            "description": product_data['name'],
                            "quantity": "1.00",
                            "amount": {
                            "value": f"{product_data['price'] / 100:.2f}",
                            "currency": "RUB"
                            },
                            "vat_code": 1,
                            "payment_mode" : "full_payment",
                            "payment_subject" : "commodity"
                        }
                    ],
                    "tax_system_code" : 1
                }
            })
        )
        
    except Exception as e:
        logger.exception("Ошибка отправки инвойса: %s", e)
        await callback.answer("❌ Ошибка выставления счёта", show_alert=True)

async def process_successful_payment(message: types.Message, bot: Bot):
    payment = message.successful_payment
    user_id = message.from_user.id

    payload_parts = payment.invoice_payload.split("/")

    product_data = config.PRODUCTS.get(payload_parts[0])
    device_id = payload_parts[-1]

    vpn_request = models.VpnRequest(telegram_id=str(message.from_user.id), device_id=int(device_id))

    vpn_key = await network_helper.post(config.SERVER_URL + config.GET_VPN_KEY_ENDPOINT, vpn_request.model_dump())

    if not vpn_key:
        await show_buy_vpn_message(message, product_data, payment, bot)
    else:
        await show_extend_vpn_message(message, product_data, payment, device_id, bot)

async def show_buy_vpn_message(message: types.Message, product_data, payment, bot: Bot):
    payload_parts = payment.invoice_payload.split("/")
    device_id = payload_parts[-1]

    vpn_order_request = models.VpnOrderRequest(telegram_id=str(message.from_user.id), duration_days=int(product_data['duration_days']))
    user_response = await network_helper.post(config.SERVER_URL + config.ADD_VPN_ORDER, vpn_order_request.model_dump())

    await message.answer(
        "✅ <b>Оплата прошла успешно!</b>\n\n"
        f"🎉 Ваш VPN активирован на {product_data['duration_days']} дней\n"
        f"💰 Сумма: {payment.total_amount / 100}₽\n"
        f"📱 Устройство: {device_id}\n"
        "📧 Данные для подключения отправляются...",
        parse_mode="HTML"
    )

    print(user_response)

    if user_response:
        await message.answer(user_response)
    else:
        await message.answer(f"К сожалению произошла ошибка отправки данных. Пожалуйста, обратитесть в {config.SUPPORT_USERNAME}\n"
                f"Укажите ваш id при обращении: {message.from_user.id}")
        return

    await _log_payment(message.from_user.id, payload_parts[0], int(device_id), payment.total_amount, payment.currency, "new")
    await notify_referrer(message.from_user.id, bot)

async def show_extend_vpn_message(message: types.Message, product_data, payment, device_id, bot: Bot):
    if product_data:

        vpn_extend = models.VpnExtendRequest(telegram_id=str(message.from_user.id), duration_days=30, device_id=int(device_id))

        status = await network_helper.post(config.SERVER_URL + config.EXTEND_VPN_ORDER_ENDPOINT, vpn_extend.model_dump())

        vpn_expiry_data = models.VpnRequest(telegram_id=str(message.from_user.id), device_id=int(device_id))
        
        expiry_date = await network_helper.post(config.SERVER_URL + config.GET_VPN_EXPIRY_DATE_ENDPOINT, vpn_expiry_data.model_dump())

        if not status:
            await message.answer(f"К сожалению произошла ошибка отправки данных. Пожалуйста, обратитесть в {config.SUPPORT_USERNAME}\n"
                f"Укажите ваш id при обращении: {message.from_user.id}")

            return

        await message.answer(
            "✅ <b>Оплата прошла успешно!</b>\n\n"
            f"🎉 Ваш VPN продлён на {product_data['duration_days']} дней\n"
            f"💰 Сумма: {payment.total_amount / 100}₽\n"
            f"📱 Устройство: {device_id}\n"
            f"📧 Дата окончания подписки: {string_formater.format_expiry_date(expiry_date)}",
            reply_markup=config.DEFAULT_KEYBOARD,
            parse_mode="HTML"
        )

        payload_parts = payment.invoice_payload.split("/")
        await _log_payment(message.from_user.id, payload_parts[0], int(device_id), payment.total_amount, payment.currency, "extend")
        await notify_referrer(message.from_user.id, bot)
    else:
        await message.answer(
            "❌ Неизвестный тип подписки. Обратитесь в поддержку: @support",
            reply_markup=config.DEFAULT_KEYBOARD,
            parse_mode="HTML"
        )

async def show_free_vpn_message(callback: types.CallbackQuery, bot: Bot):
    user_data = models.User(telegram_id=str(callback.from_user.id))

    user_bonus_status =  await network_helper.post(config.SERVER_URL + config.GET_USER_BONUS_ENDPOINT, user_data.model_dump())

    print(user_bonus_status)

    if user_bonus_status:
        await callback.answer("❌ Бонус уже был использован")
        return

    user_bonus_response = await network_helper.post(config.SERVER_URL + config.SAVE_USER_BONUS_ENDPOINT, user_data.model_dump())

    if not user_bonus_response:
        await bot.send_message(callback.from_user.id,
            f"К сожалению произошла ошибка отправки данных. Пожалуйста, обратитесть в {config.SUPPORT_USERNAME}\n"
            f"Укажите ваш id при обращении: {callback.from_user.id}")
        return

    device_id = 1
    product_data = config.PRODUCTS.get(callback.data)

    vpn_order_request = models.VpnOrderRequest(telegram_id=str(callback.from_user.id), duration_days=int(product_data['duration_days']))
    user_response = await network_helper.post(config.SERVER_URL + config.ADD_VPN_ORDER, vpn_order_request.model_dump())

    await bot.send_message(
        callback.from_user.id,
        "✅ <b>Вы успешно активировали пробный период!</b>\n\n"
        f"🎉 Ваш VPN активирован на {product_data['duration_days'] + 1} дня\n"
        f"📱 Устройство: {device_id}\n"
        "📧 Данные для подключения отправляются...",
        parse_mode="HTML"
    )

    print(user_response)

    if user_response:
        await bot.send_message(callback.from_user.id, user_response)
    else: 
        await bot.send_message(callback.from_user.id,
            f"К сожалению произошла ошибка отправки данных. Пожалуйста, обратитесть в {config.SUPPORT_USERNAME}\n"
            f"Укажите ваш id при обращении: {callback.from_user.id}")
        
        return

def get_product_id_by_name(product_name: str):
    for product_id, product_data in config.PRODUCTS.items():
        if product_data['name'] == product_name:
            return product_id
    return None

async def notify_referrer(telegram_id, bot: Bot):
    try:
        device_id = 1

        referral_bonus_request = models.User(telegram_id=str(telegram_id))
        referred_data = await network_helper.post(config.SERVER_URL + config.ADD_REFERRAL_BONUS_ENDPOINT, referral_bonus_request.model_dump())

        if not referred_data or referred_data is False or not isinstance(referred_data, dict):
            logger.debug("Нет реферала для начисления бонуса telegram_id=%s", telegram_id)
            return

        message_text = (
            "👤 <b>Один из ваших рефералов купил VPN!</b>\n"
            f"🎉 <b>Вам начислено 7 дней бесплатно на 📱 Устройство {device_id}</b>\n"
            f"📧 Дата окончания подписки: {string_formater.format_expiry_date(referred_data["expiry_date"])}"
        )
        
        await bot.send_message(
            chat_id=referred_data["referred_id"],
            text=message_text,
            parse_mode="HTML"
        )
        logger.info("Оповещение рефералу отправлено referred_id=%s", referred_data["referred_id"])
    except Exception as e:
        logger.exception("Не удалось отправить оповещение рефералу: %s", e)


async def _log_payment(telegram_id: int, product_id: str, device_id: int, amount_kopecks: int, currency: str, payment_type: str):
    try:
        await network_helper.post(
            config.SERVER_URL + config.LOG_PAYMENT_ENDPOINT,
            {
                "telegram_id": str(telegram_id),
                "amount_kopecks": amount_kopecks,
                "currency": currency or "RUB",
                "product_id": product_id,
                "device_id": device_id,
                "payment_type": payment_type,
            },
        )
    except Exception as e:
        logger.exception("Ошибка отправки лога оплаты: %s", e)