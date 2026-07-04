"""
Telegram bot + Mini App (do'kon buyurtmasi)
Kutubxona: aiogram 3.x
Render.com kabi bulut xizmatida ISHLASH uchun WEBHOOK rejimida yozilgan.
 
Kerakli ENVIRONMENT VARIABLE'lar (Render Dashboard > Environment bo'limida qo'shiladi):
    BOT_TOKEN     -> @BotFather'dan olingan token
    WEBAPP_URL    -> Mini App joylashgan HTTPS havola (masalan, GitHub Pages)
    ADMIN_CHAT_ID -> buyurtmalar keladigan chat/kanal ID (raqam)
 
Render o'zi avtomatik beradigan narsalar (qo'lda kiritish shart emas):
    PORT               -> serverning porti
    RENDER_EXTERNAL_URL -> shu botga tegishli HTTPS manzil
"""
 
import os
import json
import logging
 
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, WebAppInfo, KeyboardButton, ReplyKeyboardMarkup
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
 
# ==== SOZLAMALAR (environment variable'lardan olinadi) ====
BOT_TOKEN = os.environ["BOT_TOKEN"]
WEBAPP_URL = os.environ["WEBAPP_URL"]
ADMIN_CHAT_ID = int(os.environ["ADMIN_CHAT_ID"])
 
PORT = int(os.environ.get("PORT", 10000))
BASE_URL = os.environ["RENDER_EXTERNAL_URL"]   # Render avtomatik beradi
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{BASE_URL}{WEBHOOK_PATH}"
 
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
 
 
async def on_startup(app: web.Application):
    await bot.set_webhook(WEBHOOK_URL)
    logging.info(f"Webhook o'rnatildi: {WEBHOOK_URL}")
 async def on_shutdown(app: web.Application):
    logging.info("Xizmat to'xtayapti (webhook saqlanib qoladi)")
 
 
def main():
    app = web.Application()
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
 
    # Render'ning "hayotdaligimni bilib turish" so'rovlariga javob berish uchun
    async def health(request):
        return web.Response(text="Bot ishlayapti")
    app.router.add_get("/", health)
 
    web.run_app(app, host="0.0.0.0", port=PORT)
 
 
if __name__ == "__main__":
    main()
 
