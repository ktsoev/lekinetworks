import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

import config
import models
import network_helper

logger = logging.getLogger(__name__)

#Promocode
def get_cancel_keyboard():
     return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="❌ Отменить", 
            callback_data="promocode_cancel"
        )],
    ])

async def start(callback: types.CallbackQuery, state: FSMContext, PromoStates):
    await callback.bot.send_message(callback.from_user.id, "Введите промокод для активации:", reply_markup=get_cancel_keyboard())
    await state.set_state(PromoStates.waiting_for_promo)

async def process(message: types.Message, state: FSMContext):
    promo_code = message.text

    await message.answer(f"🔄 Проверяем ваш промокод...")

    promocode_data: models.PromocodeData = models.PromocodeData(telegram_id=str(message.from_user.id), promocode=str(promo_code))
    responseData = await network_helper.post(config.SERVER_URL + config.ACTIVATE_PROMOCODE_ENDPOINT, promocode_data.model_dump())

    # Если бэкенд вернул None или некорректные данные
    if not responseData:
        await message.answer("❌ Такой промокод не найден или уже был использован.")
        await state.clear()
        return

    try:
        promocodeResponse = models.PromocodeResponse(**responseData)
    except Exception as e:
        logger.exception("Ошибка разбора ответа промокода: %s", e)
        await message.answer("❌ Ошибка активации промокода. Попробуйте позже или обратитесь в поддержку.")
        await state.clear()
        return

    await message.answer(
        f"✅ Промокод активирован. Вы получили {promocodeResponse.duration_days} дней!\n{promocodeResponse.vpn_url}"
    )
    
    await state.clear()

async def cancel(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.bot.send_message(callback.from_user.id, "❌ Активация промокода отменена")