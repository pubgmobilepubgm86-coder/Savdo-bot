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
    return "Stars Mines Free boti 24/7 ishlamoqda!"

def run_flask():
    app.run(host="0.0.0.0", port=PORT)

# ---- BOSH MENYU TUGMALARI ----
def get_main_menu():
    builder = ReplyKeyboardBuilder()
    builder.add(types.KeyboardButton(text="💎 Stars ishlash (O'yinlar)"))
    builder.add(types.KeyboardButton(text="👤 Konchi Profili"))
    builder.add(types.KeyboardButton(text="🏆 Top Konchilar"))
    builder.add(types.KeyboardButton(text="ℹ️ Malumot / Qoidalar"))
    builder.adjust(2, 2)
    return builder.as_markup(resize_keyboard=True)

# ---- START BUYRUG'I ----
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    # Yangi foydalanuvchini bazaga qo'shamiz (Endi 10 ta bepul urinish beramiz)
    if user_id not in users_db:
        users_db[user_id] = {
            "name": message.from_user.first_name,
            "stars": 0,
            "attempts": 10 
        }
        
    welcome_text = (
        f"👋 **Salom, {message.from_user.first_name}!**\n\n"
        f"🌟 **Stars Mines Free** — mutlaqo bepul Telegram Stars ishlash platformasiga xush kelibsiz.\n"
        f"Bu yerda siz turli o'yinlar orqali tekinga Stars qazib olishingiz mumkin.\n\n"
        f"👇 Boshlash uchun pastdagi tugmalardan foydalaning!"
    )
    await message.answer(welcome_text, parse_mode="Markdown", reply_markup=get_main_menu())

# ---- TUGMALAR FUNKSIYASI ----
@dp.message(F.text == "👤 Konchi Profili")
async def show_profile(message: types.Message):
    user_id = message.from_user.id
    user = users_db.get(user_id, {"stars": 0, "attempts": 0})
    
    profile_text = (
        f"👤 **Sizning Konchi Profilingiz:**\n\n"
        f"🆔 ID: `{user_id}`\n"
        f"💎 Qazib olingan Stars: **{user['stars']} ⭐**\n"
        f"⚡ Qolgan energiya (urinishlar): **{user['attempts']}** marta"
    )
    await message.answer(profile_text, parse_mode="Markdown")

@dp.message(F.text == "🏆 Top Konchilar")
async def show_leaderboard(message: types.Message):
    if not users_db:
        await message.answer("🏆 Hozircha reyting bo'sh. Birinchi bo'lib Stars ishlashni boshlang!")
        return

    # O'yinchilarni yulduzchasi bo'yicha saralash
    sorted_users = sorted(users_db.items(), key=lambda x: x[1]['stars'], reverse=True)[:5]
    
    leader_text = "🏆 **Top-5 Stars Konchilari:**\n\n"
    for idx, (uid, udata) in enumerate(sorted_users, start=1):
        leader_text += f"{idx}. {udata['name']} — {udata['stars']} ⭐\n"
        
    await message.answer(leader_text, parse_mode="Markdown")

@dp.message(F.text == "ℹ️ Malumot / Qoidalar")
async def show_rules(message: types.Message):
    rules = (
        "ℹ️ **Stars Mines Free Qoidalari:**\n\n"
        "Botingiz orqali tekinga Stars ishlash juda oson!\n\n"
        "1️⃣ **💎 Stars ishlash** tugmasini bosing.\n"
        "2️⃣ Botga quyidagi emojilardan birini yuboring:\n"
        "   🎯 (Darts) - O'q aniq markazga tegsa (1 Star)\n"
        "   🎲 (Kubik) - Agar 6 raqami tushsa (1 Star)\n"
        "   🏀 (Basketbol) - Koptok savatga tushsa (1 Star)\n\n"
        "3️⃣ Har bir foydalanuvchiga kuniga **10 ta bepul energiya (urinish)** beriladi.\n"
        "4️⃣ Yig'ilgan Stars'lar to'g'ridan-to'g'ri balansingizga qo'shilib boradi!"
    )
    await message.answer(rules, parse_mode="Markdown")

@dp.message(F.text == "💎 Stars ishlash (O'yinlar)")
async def play_game_info(message: types.Message):
    await message.answer(
        "🎮 **Qazish (Mining) maydoniga xush kelibsiz!**\n\n"
        "Stars ishlash uchun menga quyidagi stikerlardan birini yuboring:\n"
        "🎯 (Darts)  yoki  🎲 (Kubik)  yoki  🏀 (Basketbol)\n\n"
        "Omadingizni sinab ko'ring!"
    )

# ---- O'YINLAR LOGIKASI (Darts, Kubik, Basketbol) ----
@dp.message(F.dice)
async def handle_dice(message: types.Message):
    valid_emojis = ["🎯", "🎲", "🏀"]
    
    if message.dice.emoji in valid_emojis:
        user_id = message.from_user.id
        
        if user_id not in users_db:
            await message.answer("Iltimos, avval /start buyrug'ini bosing.")
            return
            
        user = users_db[user_id]
        
        # Urinishlar qolganligini tekshirish
        if user["attempts"] <= 0:
            await message.answer("😔 Sizda hozircha energiya tugadi. Iltimos, keyinroq yana urinib ko'ring!")
            return
            
        # Urinishni bittaga kamaytiramiz
        user["attempts"] -= 1
        
        # Animatsiya tugashini kutish
        await asyncio.sleep(2.5) 
        
        # Yutuqni tekshirish logikasi
        is_win = False
        if message.dice.emoji == "🎯" and message.dice.value == 6:
            is_win = True
        elif message.dice.emoji == "🎲" and message.dice.value == 6:
            is_win = True
        elif message.dice.emoji == "🏀" and message.dice.value in [4, 5]: # Telegramda 4 va 5 qiymatlari savatga to'g'ri tushganini bildiradi
            is_win = True

        if is_win:
            user["stars"] += 1
            await message.answer(
                f"🎉 **TABRIKLAYMIZ! YUTUQ!**\nSiz 1 ta Star ishladingiz! ⭐\n\n"
                f"⚡ Qolgan energiya: {user['attempts']}", 
                parse_mode="Markdown"
            )
        else:
            await message.answer(
                f"❌ Afsuski, bu safar omad kulib boqmadi. Yana urinib ko'ring!\n\n"
                f"⚡ Qolgan energiya: {user['attempts']}"
            )

# ---- ASOSIY ISHGA TUSHIRISH ----
async def main():
    flask_thread = Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    print("Stars Mines Free boti muvaffaqiyatli ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
    
