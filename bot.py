
import os
import asyncio
import logging
import aiohttp
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart

# Loglarni konsolda ko'rish uchun sozlama
logging.basicConfig(level=logging.INFO)

# Botingizning maxfiy tokeni
BOT_TOKEN = "8845838662:AAFg9jJjjzvQlIASzEDQCLz9EcaZ3FDb6OU"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Botga /start buyrug'i berilganda
@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    await message.answer(
        "👋 Salom! Men Render platformasida 24/7 ishlovchi botman.\n\n"
        "🔍 Menga 1xBet ID raqamini yuboring, men uning formatini tekshirib beraman!"
    )

# Foydalanuvchi xabar (ID) yuborganda tekshirish qismi
@dp.message()
async def check_id(message: types.Message):
    user_input = message.text
    
    # 1xBet ID faqat raqamdan iboratligini va uzunligi 8, 9 yoki 10 xonali ekanligini tekshiramiz
    if user_input.isdigit() and 8 <= len(user_input) <= 10:
        await message.answer(f"✅ **ID formati to'g'ri:** `{user_input}`", parse_mode="Markdown")
    else:
        await message.answer("❌ **Noto'g'ri format!**\n1xBet ID faqat 8, 9 yoki 10 xonali raqamlardan iborat bo'lishi kerak.")

# === RENDER PLATFORMASI UCHUN VEB-SERVER (UYLAMASLIK UCHUN) ===
async def web_handle(request):
    return web.Response(text="Bot muvaffaqiyatli 24/7 rejimda ishlamoqda!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", web_handle)
    
    # Render muhitda beradigan portni oladi, bo'lmasa 8080 port
    port = int(os.getenv("PORT", 8080))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logging.info(f"Veb-server {port}-portda ishga tushdi.")

# === SELF-PING: BOTNI UYQUGA KETISHIDAN SAQLASH FUNKSIYASI ===
async def self_ping():
    # Render beradigan loyihangizning tashqi URL manzili
    url = os.getenv("RENDER_EXTERNAL_URL")
    if not url:
        logging.warning("RENDER_EXTERNAL_URL topilmadi. Self-ping hozircha ishga tushmadi.")
        return

    await asyncio.sleep(20)  # Bot to'liq ishlab ketishi uchun biroz kutish
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                async with session.get(url) as response:
                    logging.info(f"Self-ping muvaffaqiyatli: Status {response.status}")
            except Exception as e:
                logging.error(f"Self-pingda xatolik: {e}")
            
            # Har 10 daqiqada (600 soniya) o'ziga o'zi so'rov yuborib turadi
            await asyncio.sleep(600)

# Asosiy ishga tushirish funksiyasi
async def main():
    # Veb-serverni yuklaymiz
    await start_web_server()
    
    # Orqa fonda self-ping funksiyasini faollashtiramiz
    asyncio.create_task(self_ping())
    
    # Botni ishga tushiramiz
    logging.info("Bot polling rejimida ishga tushmoqda...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
      
