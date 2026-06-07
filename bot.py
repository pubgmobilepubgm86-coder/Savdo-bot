import os
import logging
import asyncio
from threading import Thread
from flask import Flask
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import ReplyKeyboardBuilder

# Portni Render avtomatik beradi, bo'lmasa 10000 ishlatiladi
PORT = int(os.environ.get("PORT", 10000))
# Bot tokenini Render Environment Variables qismiga qo'yganingiz ma'qul
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

# Loglar
logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ---- FLASK WEB SERVER (Render uchun) ----
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running alive!"

def run_flask():
    app.run(host="0.0.0.0", port=PORT)

# ---- TG BOT TUGMALARI ----
def get_main_menu():
    builder = ReplyKeyboardBuilder()
    builder.add(types.KeyboardButton(text="🎮 O‘yinni boshlash"))
    builder.add(types.KeyboardButton(text="👤 Profil / Balans"))
    builder.add(types.KeyboardButton(text="🏆 Top O‘yinchilar"))
    builder.add(types.KeyboardButton(text="ℹ️ Qoidalar"))
    builder.adjust(2, 2)
    return builder.as_markup(resize_keyboard=True)

# ---- HANDLERS ----
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    welcome_text = (
        f"👋 **Assalomu alaykum, {message.from_user.first_name}!**\n\n"
        f"🤖 Bepul Telegram Stars yutib olish botiga xush kelibsiz!\n"
        f"👇 Boshlash uchun pastdagi menyudan foydalaning:"
    )
    await message.answer(welcome_text, parse_mode="Markdown", reply_markup=get_main_menu())

@dp.message(lambda message: message.text == "👤 Profil / Balans")
async def show_profile(message: types.Message):
    profile_text = f"👤 **Profilingiz:**\n\n🆔 ID: `{message.from_user.id}`\n💰 Balans: **0 Stars**"
    await message.answer(profile_text, parse_mode="Markdown")

@dp.message(lambda message: message.text == "🏆 Top O‘yinchilar")
async def show_leaderboard(message: types.Message):
    await message.answer("🏆 Hozircha ro‘yxat bo‘sh. Tez orada o‘yin boshlanadi!")

@dp.message(lambda message: message.text == "ℹ️ Qoidalar")
async def show_rules(message: types.Message):
    await message.answer("ℹ️ Bot mutlaqo bepul. Vazifalarni bajaring va Stars yuting!")

# ---- ASOSIY ISHGA TUSHIRISH ----
async def main():
    # Flask serverni alohida potokda (Thread) fonda ishga tushiramiz
    flask_thread = Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    print("Bot polling rejimida ishlamoqda...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
    
