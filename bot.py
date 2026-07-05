"""
Telegram bot + Mini App (do'kon buyurtmasi)
Kutubxona: aiogram 3.x
POLLING rejimida ishlaydi (webhook EMAS) — bu ancha barqaror va sodda.
 
Kerakli ENVIRONMENT VARIABLE'lar (Render Dashboard > Environment bo'limida):
    BOT_TOKEN     -> @BotFather'dan olingan token
    WEBAPP_URL    -> Mini App joylashgan HTTPS havola (masalan, GitHub Pages)
    ADMIN_CHAT_ID -> buyurtmalar keladigan chat/kanal ID (raqam)
"""
 
import os
import json
import asyncio
import logging
 
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, WebAppInfo, KeyboardButton, ReplyKeyboardMarkup
from aiohttp import web
 
# ==== SOZLAMALAR ====
BOT_TOKEN = os.environ["BOT_TOKEN"]
WEBAPP_URL = os.environ["WEBAPP_URL"]
ADMIN_CHAT_ID = int(os.environ["ADMIN_CHAT_ID"])
PORT = int(os.environ.get("PORT", 10000))
 
logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
 
 
@dp.message(CommandStart())
async def start_handler(message: Message):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[
            KeyboardButton(text="🛒 Buyurtma berish", web_app=WebAppInfo(url=WEBAPP_URL))
        ]],
        resize_keyboard=True
    )
    await message.answer(
        "Assalomu alaykum! Buyurtma berish uchun quyidagi tugmani bosing 👇",
        reply_markup=keyboard
    )
 
 
@dp.message(F.web_app_data)
async def web_app_data_handler(message: Message):
    """Mini App'dan Telegram.WebApp.sendData() orqali kelgan ma'lumotni qabul qiladi."""
    try:
        order = json.loads(message.web_app_data.data)
    except (json.JSONDecodeError, AttributeError):
        await message.answer("Xatolik: buyurtma ma'lumotini o'qib bo'lmadi.")
        return
 
    items_lines = "\n".join(
        f"  • {item['variant']}: {item['quantity']} pachka × {item['unit_price']:,} so'm = {item['subtotal']:,} so'm"
        for item in order.get('items', []) if item['quantity'] > 0
    )
    pay_label = "Naqd" if order.get('payment_mode') == 'naqd' else "Qarzga"
 
    await message.answer(
        "✅ Buyurtmangiz qabul qilindi!\n\n"
        f"To'lov turi: {pay_label}\n"
        f"{items_lines}\n\n"
        f"Jami: {order.get('total'):,} so'm\n\n"
        "Tez orada operatorimiz siz bilan bog'lanadi."
    )
 
    admin_text = (
        "🆕 Yangi buyurtma!\n\n"
        f"To'lov turi: {pay_label}\n"
        f"{items_lines}\n\n"
        f"Jami summa: {order.get('total'):,} so'm\n\n"
        f"Ism: {order.get('full_name')}\n"
        f"Telefon: {order.get('phone')}\n"
        f"Manzil: {order.get('address')}\n"
        f"Izoh: {order.get('note') or '—'}"
    )
    await bot.send_message(ADMIN_CHAT_ID, admin_text)
 
    lat, lon = order.get('address_lat'), order.get('address_lon')
    if lat and lon:
        await bot.send_location(ADMIN_CHAT_ID, latitude=lat, longitude=lon)
 
 
# ==== Render uchun kichik "tirikman" serveri ====
# Render web-xizmat sifatida ishlashi uchun biror portni tinglab turishi shart.
# Bu server hech qanday Telegram funksiyasiga aloqador emas — faqat
# UptimeRobot va Render'ning "sog'lom holat" tekshiruvlariga javob beradi.
async def health(request):
    return web.Response(text="Bot ishlayapti (polling rejimida)")
 
 
async def run_health_server():
    app = web.Application()
    app.router.add_get("/", health)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logging.info(f"Health-server {PORT}-portda ishga tushdi")
 
 
async def main():
    await run_health_server()
    logging.info("Polling boshlandi...")
    # Ishga tushishdan oldin eski webhook (agar bo'lsa) o'chiriladi —
    # polling va webhook bir vaqtda ishlay olmaydi.
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)
 
 
if __name__ == "__main__":
    asyncio.run(main())
 
