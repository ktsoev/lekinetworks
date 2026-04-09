from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import asyncio
import config
import logging
import logging.handlers
from pathlib import Path

from dotenv import load_dotenv
import os
from decouple import config as conf

import Commands.start_command as start_command
import Commands.referal_command as referal_command
import Commands.tariffs_command as tariffs_command
import Commands.info_command as info_command
import Commands.promocode_command  as promocode_command
import Commands.home_command as home_command
import Commands.support_command as support_command
import payment_handler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
_project_root = Path(__file__).resolve().parent
log_dir = Path(os.environ.get("LOG_DIR", _project_root / "logs"))
log_dir.mkdir(parents=True, exist_ok=True)
file_handler = logging.handlers.RotatingFileHandler(
    log_dir / "bot.log",
    maxBytes=2 * 1024 * 1024,
    backupCount=5,
    encoding="utf-8",
)
file_handler.setLevel(logging.WARNING)
file_handler.setFormatter(logging.Formatter(
    "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
))
logging.getLogger().addHandler(file_handler)

env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

bot = Bot(token=conf('BOT_TOKEN', cast=str))
dp = Dispatcher()

class PromoStates(StatesGroup):
    waiting_for_promo = State()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await start_command.show_message(message)

@dp.message(lambda message: message.text == config.Bot_Commands['buy'])
async def open_tariffs_message(message: types.Message):
    await tariffs_command.show_panel(message)

@dp.message(lambda message: message.text == config.Bot_Commands['info'])
async def open_info_message(message: types.Message):
    await info_command.execute(message)

@dp.message(lambda message: message.text == config.Bot_Commands['home'])
async def open_home_message(message: types.Message):
    await home_command.execute(message)

# Backward compatibility: old reply buttons
@dp.message(lambda message: message.text in ("Оформить подписку", "Личный кабинет", "Информация"))
async def handle_legacy_reply_buttons(message: types.Message):
    await message.answer(
        "Похоже, у вас осталось старое меню.\n\n"
        "Пожалуйста, перезапустите бота командой /start — кнопки обновятся.",
        reply_markup=config.DEFAULT_KEYBOARD,
    )

#callbacks
@dp.callback_query(lambda c: c.data == "buy_vpn")
async def handle_buy_vpn_button(callback: types.CallbackQuery):
    await tariffs_command.handle_buy_vpn(callback, bot)

@dp.callback_query(lambda c: c.data == "show_referral_message")
async def handle_show_referral_button(callback: types.CallbackQuery):
    await referal_command.execute(bot, callback)

@dp.callback_query(lambda c: c.data == "show_support_message")
async def handle_show_support_button(callback: types.CallbackQuery):
    await support_command.execute(bot, callback)

@dp.callback_query(lambda c: c.data == "show_devices")
async def handle_show_devices_button(callback: types.CallbackQuery):
    await tariffs_command.handle_show_devices(callback, bot)

@dp.callback_query(lambda c: c.data.startswith("show_device/"))
async def handle_show_device(callback: types.CallbackQuery):
    await tariffs_command.handle_show_device(callback, bot)

@dp.callback_query(lambda c: c.data == "extend_vpn")
async def handle_show_extend_devices(callback: types.CallbackQuery):
    await tariffs_command.handle_show_extend_devices(callback, bot)

@dp.callback_query(lambda c: c.data.startswith("extend_device/"))
async def handle_extend_device(callback: types.CallbackQuery):
    await tariffs_command.handle_extend_vpn(callback, bot)

@dp.callback_query(lambda c: c.data.startswith(("1_month", "3_month", "6_month", "12_month")))
async def handle_payment_selection(callback: types.CallbackQuery):
    await payment_handler.create_invoice(callback, bot)
    
@dp.callback_query(lambda c: c.data == "3_days_test")
async def handle_free_vpn_callback(callback: types.CallbackQuery):
    await payment_handler.show_free_vpn_message(callback, bot)

@dp.callback_query(lambda c: c.data == "activate_promocode")
async def promo_start_callback(callback: types.CallbackQuery, state: FSMContext):
    await promocode_command.start(callback, state, PromoStates)

@dp.callback_query(lambda c: c.data == "promocode_cancel")
async def promo_cancel_callback(callback: types.CallbackQuery, state: FSMContext):
    await promocode_command.cancel(callback, state)

@dp.callback_query()
async def test(callback: types.CallbackQuery):
    print(callback.data)

@dp.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: types.PreCheckoutQuery):
    await bot.answer_pre_checkout_query(
        pre_checkout_query_id=pre_checkout_query.id,
        ok=True,
        error_message=None
    )

@dp.message(lambda message: message.successful_payment is not None)
async def process_successful_payment(message: types.Message):
    await payment_handler.process_successful_payment(message, bot)

#Promocode
@dp.message(PromoStates.waiting_for_promo)
async def process_promo(message: types.Message, state: FSMContext):
    await promocode_command.process(message, state) 

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())