import os
import logging
import asyncio
from threading import Thread
from flask import Flask
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import ReplyKeyboardBuilder

# Sizning bot tokeningiz
BOT_TOKEN = "8788707258:AAGAsvxTBVYPqeT92qJDjqr0dgnsX8eZ2Fg"
PORT = int(os.environ.get("PORT", 10000))

# Loglar
logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Foydalanuvchilar bazasi (Hozircha vaqtinchalik xotirada)
users_db = {}

# ---- FLASK WEB SERVER (Render uzluksiz ishlashi uchun) ----
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot 24/7 rejimida muvaffaqiyatli ishlamoqda!"

def run_flask():
    app.run(host="0.0.0.0", port=PORT)

# ---- BOSH MENYU TUGMALARI ----
def get_main_menu():
    builder = ReplyKeyboardBuilder()
    builder.add(types.KeyboardButton(text="🎯 Omadni sinash (Darts)"))
    builder.add(types.KeyboardButton(text="👤 Profil / Balans"))
    builder.add(types.KeyboardButton(text="🏆 Top O‘yinchilar"))
    builder.add(types.KeyboardButton(text="ℹ️ Qoidalar"))
    builder.adjust(2, 2)
    return builder.as_markup(resize_keyboard=True)

# ---- START BUYRUG'I ----
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    # Yangi foydalanuvchini bazaga qo'shamiz
    if user_id not in users_db:
        users_db[user_id] = {
            "name": message.from_user.first_name,
            "stars": 0,
            "attempts": 5 # Har bir odamga 5 tadan bepul urinish
        }
        
    welcome_text = (
        f"👋 **Salom, {message.from_user.first_name}!**\n\n"
        f"🎯 Bu yerda siz Darts o'ynab tekinga **Telegram Stars** yutib olishingiz mumkin.\n"
        f"Pastdagi tugmalar orqali o'yinni boshlang!"
    )
    await message.answer(welcome_text, parse_mode="Markdown", reply_markup=get_main_menu())

# ---- TUGMALAR FUNKSIYASI ----
@dp.message(F.text == "👤 Profil / Balans")
async def show_profile(message: types.Message):
    user_id = message.from_user.id
    user = users_db.get(user_id, {"stars": 0, "attempts": 0})
    
    profile_text = (
        f"👤 **Sizning profilingiz:**\n\n"
        f"🆔 ID: `{user_id}`\n"
        f"⭐ Yig'ilgan Stars: **{user['stars']}**\n"
        f"🎟 Qolgan urinishlar: **{user['attempts']}** marta"
    )
    await message.answer(profile_text, parse_mode="Markdown")

@dp.message(F.text == "🏆 Top O‘yinchilar")
async def show_leaderboard(message: types.Message):
    if not users_db:
        await message.answer("🏆 Hozircha reyting bo'sh.")
        return

    # O'yinchilarni yulduzchasi bo'yicha saralash
    sorted_users = sorted(users_db.items(), key=lambda x: x[1]['stars'], reverse=True)[:5]
    
    leader_text = "🏆 **Top-5 O'yinchilar:**\n\n"
    for idx, (uid, udata) in enumerate(sorted_users, start=1):
        leader_text += f"{idx}. {udata['name']} — {udata['stars']} ⭐\n"
        
    await message.answer(leader_text, parse_mode="Markdown")

@dp.message(F.text == "ℹ️ Qoidalar")
async def show_rules(message: types.Message):
    rules = (
        "ℹ️ **O'yin Qoidalari:**\n\n"
        "1. '🎯 Omadni sinash' tugmasini bosing.\n"
        "2. Botga 🎯 (darts) emojisini yuboring.\n"
        "3. Agar o'q roppa-rosa qizil markazga tegsa (6 ball), siz 1 ta Star yutasiz!\n"
        "4. Har bir foydalanuvchiga 5 ta bepul urinish beriladi."
    )
    await message.answer(rules, parse_mode="Markdown")

@dp.message(F.text == "🎯 Omadni sinash (Darts)")
async def play_game_info(message: types.Message):
    await message.answer("🎮 **O'yin boshlandi!**\n\nMenga oddiy stikerlar qatoridan 🎯 emojisini yuboring va omadingizni sinab ko'ring!")

# ---- DARTS O'YINI LOGIKASI ----
@dp.message(F.dice)
async def handle_dice(message: types.Message):
    if message.dice.emoji == "🎯":
        user_id = message.from_user.id
        
        if user_id not in users_db:
            await message.answer("Iltimos, avval /start buyrug'ini bosing.")
            return
            
        user = users_db[user_id]
        
        # Urinishlar qolganligini tekshirish
        if user["attempts"] <= 0:
            await message.answer("😔 Sizda bugungi bepul urinishlar tugadi. Ertaga yana urinib ko'ring!")
            return
            
        # Urinishni bittaga kamaytiramiz
        user["attempts"] -= 1
        
        # Telegram Darts qiymati 1 dan 6 gacha bo'ladi. 6 = markazga tegish.
        await asyncio.sleep(2) # Animatsiya tugashini kutish
        
        if message.dice.value == 6:
            user["stars"] += 1
            await message.answer(f"🎉 **BINGO! O'q markazga tegdi!**\nSiz 1 ta Star yutdingiz! 🌟\n\nQolgan urinishlaringiz: {user['attempts']}", parse_mode="Markdown")
        else:
            await message.answer(f"❌ Afsuski nishonga tegmadi. Yana urinib ko'ring.\n\nQolgan urinishlaringiz: {user['attempts']}")

# ---- ASOSIY ISHGA TUSHIRISH ----
async def main():
    # Flask serverni alohida potokda (Thread) ishga tushirish
    flask_thread = Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    print("Bot muvaffaqiyatli ishga tushdi va xabarlarni kutyapti...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
    
