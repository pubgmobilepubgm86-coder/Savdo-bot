# =====================================================================
# 1. ZARURIY KUTUBXONALAR VA MODULLAR
# =====================================================================
import os
import asyncio
import logging
import json
import random
from threading import Thread
from flask import Flask

from aiogram import Bot, Dispatcher, types, F, BaseMiddleware
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

# =====================================================================
# 2. ASOSIY SOZLAMALAR VA BAZA (JSON)
# =====================================================================
BOT_TOKEN = "8788707258:AAGHyfOlDFjJm8rspkasEVTyliQNtDZ339w"
ADMIN_ID = 8086545587
PORT = int(os.environ.get("PORT", 10000))
DATA_FILE = "bot_data.json"

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
app = Flask(__name__)

# Ma'lumotlar bazasi
users_db = {}
tasks_db = {}
promocodes_db = {}
settings_db = {"ref_reward": 5, "game_reward": 1, "mand_channel": None}
gifts_db = {
    "1": {"name": "🧸 Ayiqcha (Mines)", "price": 15},
    "2": {"name": "💎 Telegram Premium (1 oy)", "price": 250}
}

# --- BAZANI SAQLASH VA YUKLASH FUNKSIYALARI ---
def load_data():
    global users_db, tasks_db, promocodes_db, settings_db, gifts_db
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                data = json.load(f)
                users_db = {int(k): v for k, v in data.get("users_db", {}).items()}
                tasks_db = data.get("tasks_db", {})
                promocodes_db = data.get("promocodes_db", {})
                settings_db = data.get("settings_db", {"ref_reward": 5, "game_reward": 1, "mand_channel": None})
                gifts_db = data.get("gifts_db", {})
        except Exception as e:
            logging.error(f"Baza yuklashda xato: {e}")

def save_data():
    data = {
        "users_db": users_db,
        "tasks_db": tasks_db,
        "promocodes_db": promocodes_db,
        "settings_db": settings_db,
        "gifts_db": gifts_db
    }
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        logging.error(f"Baza saqlashda xato: {e}")

def init_user(user_id: int, name: str) -> dict:
    if user_id not in users_db:
        users_db[user_id] = {
            "name": name,
            "stars": 0,
            "attempts": 10,
            "completed_tasks": [],
            "used_promos": [],
            "refs": 0,
            "verified": False, 
            "ref_by": None     
        }
        save_data()
    else:
        # Eski foydalanuvchilar xatosiz ishlashi uchun yetishmayotgan kalitlarni qo'shamiz
        if "verified" not in users_db[user_id]:
            users_db[user_id]["verified"] = True
        if "ref_by" not in users_db[user_id]:
            users_db[user_id]["ref_by"] = None
    return users_db[user_id]

# =====================================================================
# 3. FSM HOLATLAR ZANJIRI
# =====================================================================
class AdminState(StatesGroup):
    waiting_for_task_photo = State()
    waiting_for_task_desc = State()
    waiting_for_task_url = State()
    waiting_for_task_chat_id = State()
    waiting_for_task_reward = State()
    waiting_for_gift_name = State()
    waiting_for_gift_price = State()
    waiting_for_promo_code = State()
    waiting_for_promo_reward = State()
    waiting_for_promo_limit = State()
    waiting_for_ref_reward = State()
    waiting_for_target_id = State()
    waiting_for_balance_val = State()
    waiting_for_game_reward = State()
    waiting_for_mand_channel = State()

class UserState(StatesGroup):
    entering_promo = State()
    waiting_for_math_answer = State()

# =====================================================================
# 4. MIDDLEWARE (TEKSHIRUV VA MAJBURIY OBUNA UCHUN)
# =====================================================================
class CheckVerifyMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        user = event.from_user
        if user.id == ADMIN_ID:
            return await handler(event, data)
        
        state: FSMContext = data.get('state')
        current_state = await state.get_state() if state else None
        
        # /start buyrug'i va matematika javoblari o'tkaziladi
        if isinstance(event, types.Message):
            if event.text and event.text.startswith("/start"):
                return await handler(event, data)
            if current_state == UserState.waiting_for_math_answer.state:
                return await handler(event, data)
                
        # Tekshiruv boshlash tugmasi o'tkaziladi
        if isinstance(event, types.CallbackQuery):
            if event.data == "start_verification":
                return await handler(event, data)
        
        # Boshqa hollarda tekshiruvdan o'tmagan bo'lsa bloklanadi
        u_data = users_db.get(user.id, {})
        if not u_data.get("verified", False):
            if isinstance(event, types.CallbackQuery):
                await event.answer("Oldin /start bosib tekshiruvdan o'ting!", show_alert=True)
            return
        
        return await handler(event, data)

class MandSubMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        bot: Bot = data['bot']
        user = event.from_user
        
        # Agar matematik holatda bo'lsa majburiy obunani so'ramay turadi
        state: FSMContext = data.get('state')
        current_state = await state.get_state() if state else None
        if current_state == UserState.waiting_for_math_answer.state:
            return await handler(event, data)

        channel = settings_db.get("mand_channel")
        
        if isinstance(event, types.CallbackQuery) and event.data == "check_mand_sub":
            return await handler(event, data)
            
        if channel and user.id != ADMIN_ID:
            try:
                member = await bot.get_chat_member(chat_id=channel, user_id=user.id)
                if member.status not in ['member', 'administrator', 'creator']:
                    kb = InlineKeyboardBuilder()
                    safe_url = f"https://t.me/{channel.replace('@', '')}"
                    kb.button(text="📢 Kanalga a'zo bo'lish", url=safe_url)
                    kb.button(text="✅ Tasdiqlash", callback_data="check_mand_sub")
                    kb.adjust(1)
                    
                    msg_text = f"⚠️ <b>Botdan foydalanish uchun rasmiy kanalimizga obuna bo'lishingiz majburiy!</b>\n\nIltimos, pastdagi tugma orqali {channel} kanaliga obuna bo'ling."
                    
                    if isinstance(event, types.Message):
                        await event.answer(msg_text, reply_markup=kb.as_markup(), parse_mode="HTML")
                    elif isinstance(event, types.CallbackQuery):
                        await event.message.answer(msg_text, reply_markup=kb.as_markup(), parse_mode="HTML")
                        await event.answer()
                    return 
            except Exception as e:
                pass 
                
        return await handler(event, data)

# Navbatma-navbat Middleware'larni ulash (Avval Verify, keyin Majburiy obuna)
dp.message.middleware(CheckVerifyMiddleware())
dp.callback_query.middleware(CheckVerifyMiddleware())
dp.message.middleware(MandSubMiddleware())
dp.callback_query.middleware(MandSubMiddleware())

@dp.callback_query(F.data == "check_mand_sub")
async def check_mand_sub_callback(callback: types.CallbackQuery):
    channel = settings_db.get("mand_channel")
    if not channel:
        await callback.message.delete()
        await send_welcome(callback.message, callback.from_user.id)
        return
    
    try:
        member = await bot.get_chat_member(chat_id=channel, user_id=callback.from_user.id)
        if member.status in ['member', 'administrator', 'creator']:
            await callback.message.delete()
            await callback.answer("✅ Obuna tasdiqlandi!", show_alert=True)
            await send_welcome(callback.message, callback.from_user.id)
        else:
            await callback.answer("❌ Hali kanalga obuna bo'lmadingiz!", show_alert=True)
    except:
        await callback.message.delete()
        await callback.message.answer("Xatolik yuz berdi. Iltimos qayta urinib ko'ring.")

# =====================================================================
# 5. MENYU KLAVIATURALARI
# =====================================================================
def main_menu(user_id: int):
    kb = ReplyKeyboardBuilder()
    kb.button(text="💎 Stars ishlash (O'yinlar)")
    kb.button(text="👤 Konchi Profili")
    kb.button(text="🏆 Top Konchilar")
    kb.button(text="ℹ️ Malumot / Qoidalar")
    kb.button(text="📋 Vazifalar (Free Stars)")
    kb.button(text="👥 Do'stlarni taklif qilish")
    kb.button(text="🎟 Promokod")
    kb.button(text="📤 Stars chiqarish")
    if user_id == ADMIN_ID:
        kb.button(text="⚙️ Admin Panel")
    kb.adjust(2, 2, 2, 2, 1)
    return kb.as_markup(resize_keyboard=True)

def games_menu():
    kb = ReplyKeyboardBuilder()
    kb.button(text="🎯 Darts")
    kb.button(text="🎲 Kubik")
    kb.button(text="🏀 Basketbol")
    kb.button(text="⬅️ Orqaga")
    kb.adjust(3, 1)
    return kb.as_markup(resize_keyboard=True)

async def send_welcome(message_or_cb, uid: int):
    text = (
        f"👋 Salom!\n\n"
        f"🌟 <b>Tulpor savdo markazi</b> — mutlaqo bepul Telegram Stars ishlash platformasiga xush kelibsiz.\n"
        f"Bu yerda siz turli o'yinlar orqali tekinga Stars qazib olishingiz mumkin.\n\n"
        f"👇 Boshlash uchun pastdagi tugmalardan foydalaning!"
    )
    if isinstance(message_or_cb, types.Message):
        await message_or_cb.answer(text, parse_mode="HTML", reply_markup=main_menu(uid))
    else:
        await message_or_cb.message.answer(text, parse_mode="HTML", reply_markup=main_menu(uid))

# =====================================================================
# 6. ASOSIY BO'LIMLAR (START VA MATEMATIK TEKSHIRUV)
# =====================================================================
@dp.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    uid = message.from_user.id
    u = init_user(uid, message.from_user.first_name)
    
    # 1. Referal id'ni ushlab qolamiz (lekin darhol pul bermaymiz)
    args = message.text.split()
    if len(args) > 1 and args[1].isdigit():
        ref_id = int(args[1])
        if not u.get("ref_by") and ref_id != uid:
            u["ref_by"] = ref_id
            save_data()

    # 2. Agar odam bot tekshiruvidan o'tmagan bo'lsa
    if not u.get("verified", False) and uid != ADMIN_ID:
        kb = InlineKeyboardBuilder()
        kb.button(text="🛡 Tekshiruvdan o'tish", callback_data="start_verification")
        await message.answer(
            "⚠️ <b>Botdan foydalanish uchun bot emasligingizni tasdiqlashingiz kerak!</b>\n\n"
            "Pastdagi tugmani bosing va oson tekshiruvdan o'ting.",
            reply_markup=kb.as_markup(), parse_mode="HTML"
        )
        return

    # 3. Oldin ro'yxatdan o'tgan bo'lsa
    await send_welcome(message, uid)

@dp.callback_query(F.data == "start_verification")
async def start_verif_cb(callback: types.CallbackQuery, state: FSMContext):
    a = random.randint(1, 10)
    b = random.randint(1, 10)
    correct_ans = a + b
    await state.update_data(math_ans=correct_ans)
    await state.set_state(UserState.waiting_for_math_answer)
    
    await callback.message.edit_text(
        f"🤖 <b>Bot emasligingizni isbotlash uchun misolni yeching:</b>\n\n"
        f"❓ <b>{a} + {b} = ?</b>\n\n"
        f"<i>👇 Javobingizni raqam orqali oddiy xabar qilib yozib yuboring (Masalan: {correct_ans})</i>", 
        parse_mode="HTML"
    )

@dp.message(UserState.waiting_for_math_answer)
async def check_math_ans(message: types.Message, state: FSMContext):
    data = await state.get_data()
    correct_ans = data.get("math_ans")
    
    if message.text.isdigit() and int(message.text) == correct_ans:
        uid = message.from_user.id
        users_db[uid]["verified"] = True
        save_data()
        await state.clear()
        
        await message.answer("✅ <b>Tekshiruvdan muvaffaqiyatli o'tdingiz!</b>", parse_mode="HTML")
        
        # Haqiqiy odamligi aniqlangach, referal egasiga pul beramiz
        ref_id = users_db[uid].get("ref_by")
        if ref_id and ref_id in users_db and ref_id not in users_db[uid]["used_promos"]:
            users_db[ref_id]["stars"] += settings_db["ref_reward"]
            users_db[ref_id]["refs"] = users_db[ref_id].get("refs", 0) + 1
            users_db[uid]["used_promos"].append(ref_id)
            save_data()
            try:
                await bot.send_message(ref_id, f"🎉 <b>Yangi do'st!</b> Sizning havolangiz orqali botga kirdi va tekshiruvdan o'tdi.\n+{settings_db['ref_reward']} ⭐", parse_mode="HTML")
            except: pass
        
        await send_welcome(message, uid)
    else:
        # Noto'g'ri topsa boshqa oson misol beramiz
        a = random.randint(1, 10)
        b = random.randint(1, 10)
        new_ans = a + b
        await state.update_data(math_ans=new_ans)
        await message.answer(
            f"❌ <b>Noto'g'ri javob!</b> Iltimos, qaytadan urinib ko'ring.\n\n"
            f"❓ <b>{a} + {b} = ?</b>\n\n"
            f"<i>👇 To'g'ri javobni xabar qilib yuboring.</i>", 
            parse_mode="HTML"
        )

# =====================================================================
# 7. QOLGAN BARCHA BO'LIMLAR (PROFIL, O'YINLAR VA ADMIN PANEL)
# =====================================================================
@dp.message(F.text == "👤 Konchi Profili")
async def profile_handler(message: types.Message):
    u = init_user(message.from_user.id, message.from_user.first_name)
    await message.answer(
        f"👤 Profil:\n🆔 {message.from_user.id}\n👥 Taklif qilgan do'stlari: {u.get('refs', 0)} ta\n"
        f"💎 Balans: {u['stars']} ⭐\n⚡ Energiya: {u['attempts']} marta", parse_mode="HTML"
    )

@dp.message(F.text == "ℹ️ Malumot / Qoidalar")
async def rules_handler(message: types.Message):
    await message.answer(
        "ℹ️ <b>Qoidalar:</b>\n\n1️⃣ 💎 Stars ishlash tugmasini bosing.\n"
        "2️⃣ Botga emojilardan birini yuboring:\n  🎯 (Darts) (2 Star)\n  🎲 (Kubik) (2 Star)\n  🏀 (Basketbol) (2 Star)\n\n"
        "3️⃣ Kuniga 10 ta bepul energiya (urinish) beriladi.", parse_mode="HTML"
    )

@dp.message(F.text == "🏆 Top Konchilar")
async def top_miners(message: types.Message):
    if not users_db: return await message.answer("🏆 Hali hech kim yo'q.")
    top = sorted(users_db.items(), key=lambda x: x[1]['stars'], reverse=True)[:5]
    txt = "🏆 <b>Top-5 Stars Konchilari:</b>\n\n"
    for i, (uid, d) in enumerate(top, 1): txt += f"{i}. {d['name']} — {d['stars']} ⭐\n"
    await message.answer(txt, parse_mode="HTML")

@dp.message(F.text == "👥 Do'stlarni taklif qilish")
async def ref_handler(message: types.Message):
    bot_info = await bot.get_me()
    link = f"https://t.me/{bot_info.username}?start={message.from_user.id}"
    await message.answer(
        f"👥 <b>Do'stlarni taklif qiling!</b>\n\n🔗 Havolangiz: <code>{link}</code>\n\n"
        f"Har bir taklif uchun: <b>{settings_db['ref_reward']} ⭐</b>", parse_mode="HTML"
    )

@dp.message(F.text == "💎 Stars ishlash (O'yinlar)")
async def games_start(message: types.Message):
    await message.answer("🎮 Menga stikerlardan birini yuboring:\n🎯 (Darts), 🎲 (Kubik) yoki 🏀 (Basketbol)", reply_markup=games_menu())

@dp.message(F.text.in_(["🎯 Darts", "🎲 Kubik", "🏀 Basketbol"]))
async def play_dice(message: types.Message):
    u = init_user(message.from_user.id, message.from_user.first_name)
    if u["attempts"] <= 0: return await message.answer("⚡ Bugungi energiya tugadi!")
    
    u["attempts"] -= 1
    save_data()
    
    emoji = message.text.split()[0]
    msg = await message.answer_dice(emoji=emoji)
    await asyncio.sleep(2.5)
    
    win = (emoji in ["🎯", "🎲"] and msg.dice.value == 6) or (emoji == "🏀" and msg.dice.value in [4, 5])
    if win:
        reward = settings_db.get("game_reward", 1)
        u["stars"] += reward
        save_data()
        await message.answer(f"🎉 <b>Yutuq!</b> +{reward} ⭐\n⚡ Qolgan energiya: {u['attempts']}", parse_mode="HTML")
    else:
        await message.answer(f"❌ <b>O'xshamadi.</b> Natija: {msg.dice.value}\n⚡ Energiya: {u['attempts']}", parse_mode="HTML")

@dp.message(F.text == "⬅️ Orqaga")
async def back_btn(message: types.Message):
    await message.answer("Asosiy menyu:", reply_markup=main_menu(message.from_user.id))

@dp.message(F.text == "📋 Vazifalar (Free Stars)")
async def tasks_menu(message: types.Message):
    u = init_user(message.from_user.id, message.from_user.first_name)
    tasks = [t for t in tasks_db if t not in u["completed_tasks"]]
    if not tasks: return await message.answer("Barcha vazifalar bajarilgan yoki hozircha vazifalar yo'q!")
        
    for tid in tasks:
        t = tasks_db[tid]
        kb = InlineKeyboardBuilder()
        safe_url = t['url'] if t['url'].startswith(("http", "tg")) else f"https://t.me/{t['url'].replace('@', '')}"
        kb.button(text="🔗 Kanal", url=safe_url)
        kb.button(text="✅ Tekshirish", callback_data=f"chk_t_{tid}")
        kb.adjust(1)
        cap = f"📝 {t['desc']}\n💎 Mukofot: {t['reward']} ⭐"
        try:
            if t['photo'] != "none": await message.answer_photo(photo=t['photo'], caption=cap, reply_markup=kb.as_markup())
            else: await message.answer(text=cap, reply_markup=kb.as_markup())
        except: await message.answer(f"⚠️ {t['desc']} vazifasida xatolik!", parse_mode="HTML")

@dp.callback_query(F.data.startswith("chk_t_"))
async def check_task(callback: types.CallbackQuery):
    tid = callback.data.split("_")[2]
    u = init_user(callback.from_user.id, callback.from_user.first_name)
    t = tasks_db.get(tid)
    if not t: return await callback.answer("Vazifa o'chirilgan!", show_alert=True)
    if tid in u["completed_tasks"]: return await callback.answer("Bajarilgan!", show_alert=True)
        
    try:
        member = await bot.get_chat_member(chat_id=t['chat_id'], user_id=callback.from_user.id)
        if member.status in ['member', 'administrator', 'creator']:
            u["stars"] += t['reward']
            u["completed_tasks"].append(tid)
            save_data()
            await callback.message.delete()
            await callback.answer(f"✅ +{t['reward']} ⭐ berildi!", show_alert=True)
        else: await callback.answer("❌ Kanalga a'zo bo'lmagansiz!", show_alert=True)
    except: await callback.answer("❌ Xatolik: Bot kanalga admin qilinmagan!", show_alert=True)

@dp.message(F.text == "🎟 Promokod")
async def promo_start(message: types.Message, state: FSMContext):
    await message.answer("🎟 Promokodni kiriting:")
    await state.set_state(UserState.entering_promo)

@dp.message(UserState.entering_promo)
async def promo_check(message: types.Message, state: FSMContext):
    code = message.text.strip()
    u = init_user(message.from_user.id, message.from_user.first_name)
    if code in promocodes_db:
        p = promocodes_db[code]
        if p["limit"] > 0 and code not in u["used_promos"]:
            u["stars"] += p["reward"]
            u["used_promos"].append(code)
            p["limit"] -= 1
            save_data()
            await message.answer(f"✅ +{p['reward']} ⭐ qo'shildi!")
        else: await message.answer("❌ Limit tugagan yoki foydalangansiz.")
    else: await message.answer("❌ Noto'g'ri kod.")
    await state.clear()

@dp.message(F.text == "📤 Stars chiqarish")
async def withdraw_menu(message: types.Message):
    u = init_user(message.from_user.id, message.from_user.first_name)
    kb = InlineKeyboardBuilder()
    for gid, g in gifts_db.items(): kb.button(text=f"🎁 {g['name']} - {g['price']} ⭐", callback_data=f"with_{gid}")
    kb.adjust(1)
    await message.answer(f"📤 Sizning balansingiz: {u['stars']} ⭐\n🎁 Quyidagi sovg'alardan birini tanlang:", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("with_"))
async def request_withdraw(callback: types.CallbackQuery):
    gid = callback.data.split("_")[1]
    uid = callback.from_user.id
    u = users_db[uid]
    g = gifts_db.get(gid)
    if g and u["stars"] >= g["price"]:
        u["stars"] -= g["price"]
        save_data()
        kb = InlineKeyboardBuilder()
        kb.button(text="✅ Tasdiqlash", callback_data=f"ok_w_{uid}_{g['price']}")
        kb.button(text="❌ Rad etish", callback_data=f"no_w_{uid}_{g['price']}")
        await bot.send_message(
            chat_id=ADMIN_ID,
            text=f"🔔 <b>Yangi so'rov!</b>\n👤 Ism: <a href='tg://user?id={uid}'>{callback.from_user.full_name}</a>\n🆔 <code>{uid}</code>\n🎁 {g['name']}\n💎 {g['price']} ⭐",
            parse_mode="HTML", reply_markup=kb.as_markup()
        )
        await callback.answer("✅ So'rov adminga yuborildi!", show_alert=True)
        await callback.message.edit_text(callback.message.html_text + "\n\n⏳ <i>So'rov ko'rib chiqilmoqda...</i>", parse_mode="HTML")
    else: await callback.answer("❌ Balans yetarli emas!", show_alert=True)

@dp.callback_query(F.data.startswith("ok_w_"))
async def accept_w(callback: types.CallbackQuery):
    uid = int(callback.data.split("_")[2])
    await callback.message.edit_text(callback.message.html_text + "\n\n✅ <b>Qabul qilindi!</b>", parse_mode="HTML")
    try: await bot.send_message(uid, "✅ <b>Tabriklaymiz!</b> Sovg'a so'rovingiz admin tomonidan tasdiqlandi!", parse_mode="HTML")
    except: pass

@dp.callback_query(F.data.startswith("no_w_"))
async def reject_w(callback: types.CallbackQuery):
    _, _, uid, price = callback.data.split("_")
    uid, price = int(uid), int(price)
    if uid in users_db: 
        users_db[uid]["stars"] += price
        save_data()
    await callback.message.edit_text(callback.message.html_text + "\n\n❌ <b>Rad etildi!</b>", parse_mode="HTML")
    try: await bot.send_message(uid, "❌ Sovg'a so'rovingiz rad etildi. Stars balansingizga qaytarildi.")
    except: pass

@dp.message(F.text == "⚙️ Admin Panel")
async def admin_panel(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Vazifa", callback_data="adm_add_task")
    kb.button(text="🗑 Vazifa", callback_data="adm_del_task")
    kb.button(text="🎁 Sovg'a", callback_data="adm_add_gift")
    kb.button(text="🗑 Sovg'a", callback_data="adm_del_gift")
    kb.button(text="🎟 Promo", callback_data="adm_add_promo")
    kb.button(text="🔗 Ref Narx", callback_data="adm_edit_ref")
    kb.button(text="🎮 O'yin Narxi", callback_data="adm_edit_game") 
    kb.button(text="💰 Balans", callback_data="adm_edit_bal")
    kb.button(text="📢 Majburiy Obuna", callback_data="adm_mand_sub") 
    kb.button(text="👥 Referallar", callback_data="adm_ref_stats") 
    kb.button(text="📊 Statistika", callback_data="adm_get_stats")
    kb.adjust(2, 2, 2, 2, 2, 1)
    await message.answer("👨‍💻 <b>Admin Panel</b>", parse_mode="HTML", reply_markup=kb.as_markup())

@dp.callback_query(F.data == "adm_ref_stats")
async def a_ref_stats(callback: types.CallbackQuery):
    sorted_users = sorted(users_db.items(), key=lambda x: x[1].get('refs', 0), reverse=True)
    txt = "👥 <b>Referal statistikasi (Top 20):</b>\n\n"
    has_refs = False
    for uid, udata in sorted_users[:20]:
        if udata.get('refs', 0) > 0:
            txt += f"👤 {udata['name']} (<code>{uid}</code>) - {udata.get('refs', 0)} ta\n"
            has_refs = True
    if not has_refs: txt += "Hali hech kim referal taklif qilmadi."
    await callback.message.answer(txt, parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "adm_mand_sub")
async def a_mand1(callback: types.CallbackQuery, state: FSMContext):
    kb = InlineKeyboardBuilder()
    kb.button(text="❌ O'chirish", callback_data="disable_mand_sub")
    current = settings_db.get('mand_channel', "Yo'q")
    await callback.message.answer(f"Hozirgi: <b>{current}</b>\nYangi kanalni bering (yoki o'chiring):", parse_mode="HTML", reply_markup=kb.as_markup())
    await state.set_state(AdminState.waiting_for_mand_channel)
    
@dp.callback_query(F.data == "disable_mand_sub")
async def a_mand_disable(callback: types.CallbackQuery, state: FSMContext):
    settings_db["mand_channel"] = None
    save_data()
    await callback.message.edit_text("✅ Majburiy obuna o'chirildi!")
    await state.clear()
    
@dp.message(AdminState.waiting_for_mand_channel)
async def a_mand2(message: types.Message, state: FSMContext):
    channel = message.text.strip()
    if not channel.startswith("@"): channel = "@" + channel
    settings_db["mand_channel"] = channel
    save_data()
    await message.answer(f"✅ Obuna {channel} ga o'rnatildi!")
    await state.clear()

@dp.callback_query(F.data == "adm_get_stats")
async def a_stats(callback: types.CallbackQuery):
    await callback.answer(f"📊 Jami a'zolar: {len(users_db)} ta", show_alert=True)

@dp.callback_query(F.data == "adm_edit_ref")
async def a_ref1(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Yangi ref narxini yozing:")
    await state.set_state(AdminState.waiting_for_ref_reward)

@dp.message(AdminState.waiting_for_ref_reward)
async def a_ref2(message: types.Message, state: FSMContext):
    if message.text.isdigit():
        settings_db["ref_reward"] = int(message.text)
        save_data()
        await message.answer("✅ Saqlandi!")
    await state.clear()

@dp.callback_query(F.data == "adm_edit_game")
async def a_game1(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Yangi o'yin yutuq narxini kiriting:")
    await state.set_state(AdminState.waiting_for_game_reward)

@dp.message(AdminState.waiting_for_game_reward)
async def a_game2(message: types.Message, state: FSMContext):
    if message.text.isdigit():
        settings_db["game_reward"] = int(message.text)
        save_data()
        await message.answer("✅ Saqlandi!")
    await state.clear()

@dp.callback_query(F.data == "adm_add_task")
async def a_task1(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("1/5: Rasm (yoki 'none'):")
    await state.set_state(AdminState.waiting_for_task_photo)

@dp.message(AdminState.waiting_for_task_photo)
async def a_task2(message: types.Message, state: FSMContext):
    p_id = message.photo[-1].file_id if message.photo else "none"
    desc = message.caption if message.photo else message.text
    await state.update_data(p=p_id, d=desc)
    await message.answer("2/5: Kanal havolasi (URL):")
    await state.set_state(AdminState.waiting_for_task_url)

@dp.message(AdminState.waiting_for_task_url)
async def a_task3(message: types.Message, state: FSMContext):
    await state.update_data(u=message.text)
    await message.answer("3/5: ID yoki Username:")
    await state.set_state(AdminState.waiting_for_task_chat_id)

@dp.message(AdminState.waiting_for_task_chat_id)
async def a_task4(message: types.Message, state: FSMContext):
    await state.update_data(c=message.text)
    await message.answer("4/5: Mukofot:")
    await state.set_state(AdminState.waiting_for_task_reward)

@dp.message(AdminState.waiting_for_task_reward)
async def a_task5(message: types.Message, state: FSMContext):
    if message.text.isdigit():
        d = await state.get_data()
        tasks_db[str(len(tasks_db) + 1)] = {"photo": d['p'], "desc": d['d'], "url": d['u'], "chat_id": d['c'], "reward": int(message.text)}
        save_data()
        await message.answer("✅ Qo'shildi!")
    await state.clear()

@dp.callback_query(F.data == "adm_del_task")
async def a_deltask_list(callback: types.CallbackQuery):
    kb = InlineKeyboardBuilder()
    for tid, t in tasks_db.items(): kb.button(text=f"🗑 {t['desc'][:15]}...", callback_data=f"del_t_{tid}")
    kb.adjust(1)
    await callback.message.answer("Tanlang:", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("del_t_"))
async def a_deltask_action(callback: types.CallbackQuery):
    tasks_db.pop(callback.data.split("_")[2], None)
    save_data()
    await callback.message.edit_text("✅ O'chirildi!")

@dp.callback_query(F.data == "adm_add_gift")
async def a_gift1(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("1/2: Nom:")
    await state.set_state(AdminState.waiting_for_gift_name)

@dp.message(AdminState.waiting_for_gift_name)
async def a_gift2(message: types.Message, state: FSMContext):
    await state.update_data(n=message.text)
    await message.answer("2/2: Narxi:")
    await state.set_state(AdminState.waiting_for_gift_price)

@dp.message(AdminState.waiting_for_gift_price)
async def a_gift3(message: types.Message, state: FSMContext):
    if message.text.isdigit():
        d = await state.get_data()
        gifts_db[str(len(gifts_db) + 1)] = {"name": d['n'], "price": int(message.text)}
        save_data()
        await message.answer("✅ Qo'shildi!")
    await state.clear()

@dp.callback_query(F.data == "adm_del_gift")
async def a_delgift_list(callback: types.CallbackQuery):
    kb = InlineKeyboardBuilder()
    for gid, g in gifts_db.items(): kb.button(text=f"🗑 {g['name']}", callback_data=f"del_g_{gid}")
    kb.adjust(1)
    await callback.message.answer("Tanlang:", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("del_g_"))
async def a_delgift_action(callback: types.CallbackQuery):
    gifts_db.pop(callback.data.split("_")[2], None)
    save_data()
    await callback.message.edit_text("✅ O'chirildi!")

@dp.callback_query(F.data == "adm_add_promo")
async def a_promo1(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("1/3: Promo matni:")
    await state.set_state(AdminState.waiting_for_promo_code)

@dp.message(AdminState.waiting_for_promo_code)
async def a_promo2(message: types.Message, state: FSMContext):
    await state.update_data(c=message.text)
    await message.answer("2/3: Mukofot:")
    await state.set_state(AdminState.waiting_for_promo_reward)

@dp.message(AdminState.waiting_for_promo_reward)
async def a_promo3(message: types.Message, state: FSMContext):
    await state.update_data(r=int(message.text))
    await message.answer("3/3: Limit:")
    await state.set_state(AdminState.waiting_for_promo_limit)

@dp.message(AdminState.waiting_for_promo_limit)
async def a_promo4(message: types.Message, state: FSMContext):
    d = await state.get_data()
    promocodes_db[d['c']] = {"reward": d['r'], "limit": int(message.text)}
    save_data()
    await message.answer("✅ Saqlandi!")
    await state.clear()

@dp.callback_query(F.data == "adm_edit_bal")
async def a_bal1(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Foydalanuvchi ID raqamini kiriting:")
    await state.set_state(AdminState.waiting_for_target_id)

@dp.message(AdminState.waiting_for_target_id)
async def a_bal2(message: types.Message, state: FSMContext):
    if message.text.isdigit() and int(message.text) in users_db:
        await state.update_data(i=int(message.text))
        await message.answer(f"Qancha Stars qo'shmoqchisiz (Yoki ayirish uchun -10):")
        await state.set_state(AdminState.waiting_for_balance_val)
    else:
        await message.answer("❌ ID topilmadi.")
        await state.clear()

@dp.message(AdminState.waiting_for_balance_val)
async def a_bal3(message: types.Message, state: FSMContext):
    try:
        d = await state.get_data()
        users_db[d['i']]['stars'] = max(0, users_db[d['i']]['stars'] + int(message.text))
        save_data()
        await message.answer("✅ Balans tahrirlandi!")
    except: pass
    await state.clear()

# =====================================================================
# KEEP-ALIVE SERVER (RENDER UCHUN)
# =====================================================================
@app.route('/')
def index(): return "Bot Online!"

def start_flask(): app.run(host="0.0.0.0", port=PORT)

async def main():
    load_data()
    Thread(target=start_flask, daemon=True).start()
    logging.info("Bot tizimi ishga tushirildi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
   
