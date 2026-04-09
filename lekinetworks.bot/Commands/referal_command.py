from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

async def execute(bot: Bot, callback: types.CallbackQuery):
    bot_username = (await bot.get_me()).username
    ref_link = f"https://t.me/{bot_username}?start={callback.from_user.id}"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="📢 Поделиться", 
            url=f"https://t.me/share/url?url={ref_link}"
        )]
    ])
    
    await callback.bot.send_message(
        callback.from_user.id,
        f"🎁 Пригласи друга и получи *7 дней VPN бесплатно*\n\n"
        f"За каждого пользователя, оформившего подписку по твоей ссылке, "
        f"мы добавим +7 дней к твоему тарифу.\n"
        f"Количество бонусных дней не ограничено ♾️\n\n"
        f"🔗 Твоя реферальная ссылка:\n"
        f"`{ref_link}`",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )