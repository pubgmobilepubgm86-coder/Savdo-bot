import os
import logging
import asyncio
from threading import Thread
from flask import Flask
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

# ---- SOZLAMALAR ----
BOT_TOKEN = "8788707258:AAGAsvxTBVYPqeT92qJDjqr0dgnsX8eZ2Fg"
PORT = int(os.environ.get("PORT", 10000))
ADMIN_ID = 8086545587  # Sizning ID raqamingiz

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
# FSM ishlashi uchun MemoryStorage ulaymiz
dp = Dispatcher(storage=MemoryStorage())

# ---- BAZALAR (Vaqtinchalik xotirada) ----
users_db = {}
tasks_db = {}  # Vazifalar ro'yxati
gifts_db = {
    "1": {"name": "🧸 Ayiqcha", "price": 15},
    "2": {"name": "💎 Telegram Premium (1 oy)", "price": 250}
}

# ---- FLASK WEB SERVER ----
app = Flask(__name__)

@app.route('/')
def home():
    return "Stars Mines Free boti 24/7 ishlamoqda!"

def run_flask():
    app.run(host="0.0.0.0", port=PORT)

# ---- FSM HOLATLARI (Admin vazifa/sovg'a qo'shishi uchun) ----
class TaskState(StatesGroup):
    waiting_for_photo = State()
    waiting_for_url = State()
    waiting_for_reward = State()

class GiftState(StatesGroup):
    waiting_for_name = State()
    waiting_for_price = State()

# ---- BOSH MENYU TUGMALARI ----
def get_main_menu(user_id):
    builder = ReplyKeyboardBuilder()
    builder.add(types.KeyboardButton(text="💎 Stars ishlash (O'yinlar)"))
    builder.add(types.KeyboardButton(text="📋 Vazifalar (Free Stars)"))
    builder.add(types.KeyboardButton(text="👤 Profil"))
    builder.add(types.KeyboardButton(text="📤 Stars chiqarish"))
    builder.add(types.KeyboardButton(text="🏆 Top Konchilar"))
    builder.add(types.KeyboardButton(text="ℹ️ Malumot / Qoidalar"))
    
    # Faqat adminga ko'rinadigan tugma
    if user_id == ADMIN_ID:
        builder.add(types.KeyboardButton(text="⚙️ Admin Panel"))
        
    builder.adjust(2, 2, 2, 1) # Tugmalarni 2 tadan qilib taxlash
    return builder.as_markup(resize_keyboard=True)

# ---- START VA ASOSIY MENYULAR ----
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    if user_id not in users_db:
        users_db[user_id] = {
            "name": message.from_user.first_name,
            "stars": 0,
            "attempts": 10,
            "completed_tasks": []
        }
        
    welcome_text = (
        f"👋 **Salom, {message.from_user.first_name}!**\n\n"
        f"🌟 **Stars Mines Free** platformasiga xush kelibsiz.\n"
        f"👇 Boshlash uchun pastdagi tugmalardan foydalaning!"
    )
    await message.answer(welcome_text, parse_mode="Markdown", reply_markup=get_main_menu(user_id))

@dp.message(F.text == "👤 Profil")
async def show_profile(message: types.Message):
    user_id = message.from_user.id
    user = users_db.get(user_id, {"stars": 0, "attempts": 0})
    
    profile_text = (
        f"👤 **Sizning Profilingiz:**\n\n"
        f"🆔 ID: `{user_id}`\n"
        f"💎 Balansingiz: **{user['stars']} ⭐**\n"
        f"⚡ O'yin energiyasi: **{user['attempts']}** marta"
    )
    await message.answer(profile_text, parse_mode="Markdown")

@dp.message(F.text == "ℹ️ Malumot / Qoidalar")
async def show_rules(message: types.Message):
    rules = (
        "ℹ️ **Malumot:**\n"
        "Bu botda siz har hil vazifalar, oʻyinlar va promocodlar orqali Stars ishlab oʻz hisobingizga oʻtkaza olasiz. Barcha sovg'alarni olish uchun minimal miqdor — **15 ta Stars**.\n\n"
        "⚠️ **Qoidalar:**\n"
        "🛑 Botga nakrutka ursangiz (yoki soxta profillardan kirsangiz) hisobingiz so'zsiz bloklanadi, ogoh boʻling!"
    )
    await message.answer(rules, parse_mode="Markdown")

# ---- VAZIFALAR QISMI (FOYDALANUVCHI UCHUN) ----
@dp.message(F.text == "📋 Vazifalar (Free Stars)")
async def show_tasks(message: types.Message):
    user_id = message.from_user.id
    user = users_db.get(user_id)
    
    available_tasks = [t_id for t_id in tasks_db if t_id not in user.get("completed_tasks", [])]
    
    if not available_tasks:
        await message.answer("🎉 Hozircha barcha vazifalarni bajarib bo'ldingiz yoki yangi vazifalar qo'shilmagan. Keyinroq tekshiring!")
        return

    await message.answer("👇 **Mavjud vazifalar ro'yxati:**")
    
    for t_id in available_tasks:
        task = tasks_db[t_id]
        
        # Tugma yaratish
        btn = InlineKeyboardBuilder()
        btn.button(text="🔗 Kanal/Guruhga kirish", url=task['url'])
        btn.button(text="✅ Bajardim (Tekshirish)", callback_data=f"check_task_{t_id}")
        btn.adjust(1)
        
        caption_text = f"📝 **Vazifa:** {task['desc']}\n💎 **Mukofot:** {task['reward']} Stars"
        
        if task.get('photo'):
            await message.answer_photo(photo=task['photo'], caption=caption_text, parse_mode="Markdown", reply_markup=btn.as_markup())
        else:
            await message.answer(caption_text, parse_mode="Markdown", reply_markup=btn.as_markup())

@dp.callback_query(F.data.startswith("check_task_"))
async def verify_task(callback: types.CallbackQuery):
    task_id = callback.data.split("_")[2]
    user_id = callback.from_user.id
    
    if task_id in tasks_db:
        # Haqiqiy loyihada bu yerda obunani tekshirish kodi bo'ladi (bot admin bo'lishi kerak).
        # Hozircha foydalanuvchini rag'batlantirish uchun avtomatik tasdiqlaymiz.
        user = users_db[user_id]
        if task_id not in user.get("completed_tasks", []):
            reward = tasks_db[task_id]['reward']
            user["stars"] += reward
            user.setdefault("completed_tasks", []).append(task_id)
            await callback.message.edit_reply_markup() # Tugmani olib tashlaymiz
            await callback.answer(f"✅ Vazifa tasdiqlandi! Siz {reward} Stars yutdingiz.", show_alert=True)
            await bot.send_message(user_id, f"💎 Balansingizga {reward} Stars qo'shildi!")
        else:
            await callback.answer("Siz bu vazifani avval bajargansiz!", show_alert=True)

# ---- STARS CHIQARISH QISMI ----
@dp.message(F.text == "📤 Stars chiqarish")
async def show_withdrawal(message: types.Message):
    user_id = message.from_user.id
    user_stars = users_db.get(user_id, {}).get("stars", 0)
    
    text = f"📤 **Stars chiqarish bo'limi**\n\nSizning balansingiz: **{user_stars} ⭐**\n(Minimal yechish: 15 Stars)\n\n🎁 **Quyidagi sovg'alardan birini tanlang:**"
    
    btn = InlineKeyboardBuilder()
    for g_id, gift in gifts_db.items():
        btn.button(text=f"{gift['name']} - {gift['price']} ⭐", callback_data=f"buy_gift_{g_id}")
    btn.adjust(1)
    
    await message.answer(text, parse_mode="Markdown", reply_markup=btn.as_markup())

@dp.callback_query(F.data.startswith("buy_gift_"))
async def process_buy_gift(callback: types.CallbackQuery):
    gift_id = callback.data.split("_")[2]
    user_id = callback.from_user.id
    user = users_db.get(user_id)
    
    if gift_id in gifts_db:
        gift = gifts_db[gift_id]
        
        if user["stars"] < 15:
            await callback.answer("❌ Kechirasiz, chiqarib olish uchun balansingizda kamida 15 Stars bo'lishi kerak!", show_alert=True)
            return
            
        if user["stars"] < gift["price"]:
            await callback.answer(f"❌ Kechirasiz, {gift['name']} olish uchun balansingiz yetarli emas!", show_alert=True)
            return
            
        # Balansdan yechamiz
        user["stars"] -= gift["price"]
        
        # Adminga xabar yuboramiz
        admin_msg = f"🔔 **Yangi sovg'a so'rovi!**\n\n👤 Foydalanuvchi: {callback.from_user.full_name} (ID: `{user_id}`)\n🎁 Tanladi: {gift['name']}\n💎 To'ladi: {gift['price']} Stars"
        await bot.send_message(ADMIN_ID, admin_msg, parse_mode="Markdown")
        
        await callback.answer("✅ So'rovingiz adminga yuborildi. Tez orada siz bilan bog'lanishadi!", show_alert=True)
        await bot.send_message(user_id, "✅ So'rov qabul qilindi. Admin tekshiruvidan so'ng sovg'angiz taqdim etiladi.")

# ---- O'YINLAR (DICE) LOGIKASI ----
@dp.message(F.text == "💎 Stars ishlash (O'yinlar)")
async def play_game_info(message: types.Message):
    await message.answer("🎮 Menga quyidagi stikerlardan birini yuboring:\n🎯 (Darts), 🎲 (Kubik) yoki 🏀 (Basketbol)\n\nOmadingizni sinab ko'ring!")

@dp.message(F.dice)
async def handle_dice(message: types.Message):
    valid_emojis = ["🎯", "🎲", "🏀"]
    if message.dice.emoji in valid_emojis:
        user_id = message.from_user.id
        if user_id not in users_db:
            return
        user = users_db[user_id]
        
        if user["attempts"] <= 0:
            await message.answer("😔 Bugungi energiya tugadi.")
            return
            
        user["attempts"] -= 1
        await asyncio.sleep(2.5) 
        
        is_win = False
        if message.dice.value == 6 and message.dice.emoji in ["🎯", "🎲"]:
            is_win = True
        elif message.dice.emoji == "🏀" and message.dice.value in [4, 5]:
            is_win = True

        if is_win:
            user["stars"] += 1
            await message.answer(f"🎉 **YUTUQ!** Siz 1 ta Star ishladingiz! ⭐\n⚡ Qolgan energiya: {user['attempts']}", parse_mode="Markdown")
        else:
            await message.answer(f"❌ Afsuski nishonga tegmadi.\n⚡ Qolgan energiya: {user['attempts']}")

# ---- ADMIN PANEL LOGIKASI ----
@dp.message(F.text == "⚙️ Admin Panel")
async def admin_panel(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
        
    btn = InlineKeyboardBuilder()
    btn.button(text="➕ Vazifa qo'shish", callback_data="admin_add_task")
    btn.button(text="🎁 Sovg'a qo'shish", callback_data="admin_add_gift")
    btn.adjust(1)
    
    await message.answer("👨‍💻 **Admin Panelga xush kelibsiz!**\nNimani o'zgartiramiz?", parse_mode="Markdown", reply_markup=btn.as_markup())

# Vazifa qo'shish FSM
@dp.callback_query(F.data == "admin_add_task")
async def admin_add_task_start(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID: return
    await callback.message.answer("1️⃣ Vazifa uchun **Rasm yuboring** va rasmning **Tagiga (Caption)** vazifa nomini yozing.")
    await state.set_state(TaskState.waiting_for_photo)

@dp.message(TaskState.waiting_for_photo, F.photo)
async def task_get_photo(message: types.Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    desc = message.caption if message.caption else "Yangi vazifa"
    await state.update_data(photo=photo_id, desc=desc)
    
    await message.answer("2️⃣ Endi kanal yoki guruh **Havolasini (URL)** yuboring.\nMasalan: https://t.me/kanal_nomi")
    await state.set_state(TaskState.waiting_for_url)

@dp.message(TaskState.waiting_for_url)
async def task_get_url(message: types.Message, state: FSMContext):
    await state.update_data(url=message.text)
    await message.answer("3️⃣ Ushbu vazifani bajargani uchun necha **Stars (Mukofot)** beramiz? (Faqat raqam yozing)")
    await state.set_state(TaskState.waiting_for_reward)

@dp.message(TaskState.waiting_for_reward)
async def task_get_reward(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Iltimos, faqat raqam yozing!")
        return
        
    data = await state.get_data()
    task_id = str(len(tasks_db) + 1)
    
    tasks_db[task_id] = {
        "photo": data['photo'],
        "desc": data['desc'],
        "url": data['url'],
        "reward": int(message.text)
    }
    
    await message.answer("✅ **Yangi vazifa muvaffaqiyatli qo'shildi!** Endi u barchaga ko'rinadi.", parse_mode="Markdown")
    await state.clear()

# Sovg'a qo'shish FSM
@dp.callback_query(F.data == "admin_add_gift")
async def admin_add_gift_start(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID: return
    await callback.message.answer("1️⃣ Sovg'a nomini yuboring (Masalan: 🚗 Mashina yoki 🎫 Promokod)")
    await state.set_state(GiftState.waiting_for_name)

@dp.message(GiftState.waiting_for_name)
async def gift_get_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("2️⃣ Bu sovg'aning narxi necha Stars? (Faqat raqam)")
    await state.set_state(GiftState.waiting_for_price)

@dp.message(GiftState.waiting_for_price)
async def gift_get_price(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Iltimos, faqat raqam yozing!")
        return
        
    data = await state.get_data()
    gift_id = str(len(gifts_db) + 1)
    
    gifts_db[gift_id] = {
        "name": data['name'],
        "price": int(message.text)
    }
    
    await message.answer("✅ **Yangi sovg'a qo'shildi!**", parse_mode="Markdown")
    await state.clear()

# ---- ASOSIY ISHGA TUSHIRISH ----
async def main():
    flask_thread = Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    print("Mukammal bot ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
    
