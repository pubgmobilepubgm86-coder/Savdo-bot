# =====================================================================
# 1. ZARURIY KUTUBXONALAR VA MODULLAR
# =====================================================================
import os
import asyncio
import logging
from threading import Thread
from flask import Flask

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

# =====================================================================
# 2. ASOSIY SOZLAMALAR VA BAZA
# =====================================================================
BOT_TOKEN = "8788707258:AAGAsvxTBVYPqeT92qJDjqr0dgnsX8eZ2Fg"
ADMIN_ID = 8086545587
ADMIN_USERNAME = "pubgmobilepubgm86_coder"
PORT = int(os.environ.get("PORT", 10000))

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
app = Flask(__name__)

# Ma'lumotlar bazasi (Xotirada)
users_db = {}
tasks_db = {}
promocodes_db = {}
settings_db = {"ref_reward": 5}
gifts_db = {
    "1": {"name": "🧸 Ayiqcha (Mines)", "price": 15},
    "2": {"name": "💎 Telegram Premium (1 oy)", "price": 250}
}

def init_user(user_id: int, name: str) -> dict:
    if user_id not in users_db:
        users_db[user_id] = {
            "name": name,
            "stars": 0,
            "attempts": 10,
            "completed_tasks": [],
            "used_promos": []
        }
    return users_db[user_id]

# =====================================================================
# 3. KEEP-ALIVE SERVER (RENDER UCHUN)
# =====================================================================
@app.route('/')
def index():
    return "Bot Online!"

def start_flask():
    app.run(host="0.0.0.0", port=PORT)

# =====================================================================
# 4. FSM HOLATLAR ZANJIRI (ADMIN VA USER UCHUN)
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

class UserState(StatesGroup):
    entering_promo = State()

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

# =====================================================================
# 6. ASOSIY BO'LIMLAR (START, PROFIL, MALUMOT)
# =====================================================================
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    uid = message.from_user.id
    init_user(uid, message.from_user.first_name)
    
    args = message.text.split()
    if len(args) > 1 and args[1].isdigit():
        ref_id = int(args[1])
        if ref_id in users_db and ref_id != uid:
            if ref_id not in users_db[uid]["used_promos"]:
                users_db[ref_id]["stars"] += settings_db["ref_reward"]
                users_db[uid]["used_promos"].append(ref_id)
                try:
                    await bot.send_message(ref_id, f"🎉 <b>Yangi do'st!</b> Havolangiz orqali qo'shildi.\n+{settings_db['ref_reward']} ⭐", parse_mode="HTML")
                except: pass

    await message.answer(
        f"👋 Salom, {message.from_user.first_name}!\n\n"
        f"🌟 <b>Stars Mines Free</b> — mutlaqo bepul Telegram Stars ishlash platformasiga xush kelibsiz.\n"
        f"Bu yerda siz turli o'yinlar orqali tekinga Stars qazib olishingiz mumkin.\n\n"
        f"👇 Boshlash uchun pastdagi tugmalardan foydalaning!",
        parse_mode="HTML", reply_markup=main_menu(uid)
    )

@dp.message(F.text == "👤 Konchi Profili")
async def profile_handler(message: types.Message):
    u = init_user(message.from_user.id, message.from_user.first_name)
    await message.answer(
        f"👤 Profil:\n"
        f"🆔 {message.from_user.id}\n"
        f"💎 Balans: {u['stars']} ⭐\n"
        f"⚡ Energiya: {u['attempts']} marta",
        parse_mode="HTML"
    )

@dp.message(F.text == "ℹ️ Malumot / Qoidalar")
async def rules_handler(message: types.Message):
    await message.answer(
        "ℹ️ <b>Stars Mines Free Qoidalari:</b>\n\n"
        "Botingiz orqali tekinga Stars ishlash juda oson!\n\n"
        "1️⃣ 💎 Stars ishlash tugmasini bosing.\n"
        "2️⃣ Botga emojilardan birini yuboring:\n"
        "  🎯 (Darts) - O'q aniq markazga tegsa (2 Star)\n"
        "  🎲 (Kubik) - Agar 6 raqami tushsa (2 Star)\n"
        "  🏀 (Basketbol) - Koptok savatga tushsa (2 Star)\n\n"
        "3️⃣ Har bir foydalanuvchiga kuniga 10 ta bepul energiya (urinish) beriladi.\n"
        "4️⃣ Yig'ilgan Stars'lar to'g'ridan-to'g'ri balansingizga qo'shilib boradi!",
        parse_mode="HTML"
    )

@dp.message(F.text == "🏆 Top Konchilar")
async def top_miners(message: types.Message):
    if not users_db:
        return await message.answer("🏆 Hali hech kim yo'q.")
    top = sorted(users_db.items(), key=lambda x: x[1]['stars'], reverse=True)[:5]
    txt = "🏆 <b>Top-5 Stars Konchilari:</b>\n\n"
    for i, (uid, d) in enumerate(top, 1):
        txt += f"{i}. {d['name']} — {d['stars']} ⭐\n"
    await message.answer(txt, parse_mode="HTML")

@dp.message(F.text == "👥 Do'stlarni taklif qilish")
async def ref_handler(message: types.Message):
    bot_info = await bot.get_me()
    link = f"https://t.me/{bot_info.username}?start={message.from_user.id}"
    await message.answer(
        f"👥 <b>Do'stlarni taklif qiling!</b>\n\n"
        f"🔗 Havolangiz: <code>{link}</code>\n\n"
        f"Har bir taklif uchun mukofot: <b>{settings_db['ref_reward']} ⭐</b>", parse_mode="HTML"
    )

# =====================================================================
# 7. O'YINLAR (DICE)
# =====================================================================
@dp.message(F.text == "💎 Stars ishlash (O'yinlar)")
async def games_start(message: types.Message):
    await message.answer("🎮 Menga stikerlardan birini yuboring:\n🎯 (Darts), 🎲 (Kubik) yoki 🏀 (Basketbol)", reply_markup=games_menu())

@dp.message(F.text.in_(["🎯 Darts", "🎲 Kubik", "🏀 Basketbol"]))
async def play_dice(message: types.Message):
    u = init_user(message.from_user.id, message.from_user.first_name)
    if u["attempts"] <= 0:
        return await message.answer("⚡ Bugungi energiya tugadi!")
    
    u["attempts"] -= 1
    emoji = message.text.split()[0]
    msg = await message.answer_dice(emoji=emoji)
    await asyncio.sleep(2.5)
    
    win = (emoji in ["🎯", "🎲"] and msg.dice.value == 6) or (emoji == "🏀" and msg.dice.value in [4, 5])
    if win:
        u["stars"] += 2
        await message.answer(f"🎉 <b>Yutuq!</b> +2 ⭐\n⚡ Qolgan energiya: {u['attempts']}", parse_mode="HTML")
    else:
        await message.answer(f"❌ <b>O'xshamadi.</b> Natija: {msg.dice.value}\n⚡ Energiya: {u['attempts']}", parse_mode="HTML")

@dp.message(F.text == "⬅️ Orqaga")
async def back_btn(message: types.Message):
    await message.answer("Asosiy menyu:", reply_markup=main_menu(message.from_user.id))

# =====================================================================
# 8. VAZIFALAR VA PROMOKOD
# =====================================================================
@dp.message(F.text == "📋 Vazifalar (Free Stars)")
async def tasks_menu(message: types.Message):
    u = init_user(message.from_user.id, message.from_user.first_name)
    tasks = [t for t in tasks_db if t not in u["completed_tasks"]]
    if not tasks:
        return await message.answer("Barcha vazifalar bajarilgan!")
        
    for tid in tasks:
        t = tasks_db[tid]
        kb = InlineKeyboardBuilder()
        kb.button(text="🔗 Kanal", url=t['url'])
        kb.button(text="✅ Tekshirish", callback_data=f"chk_t_{tid}")
        kb.adjust(1)
        
        cap = f"📝 {t['desc']}\n💎 Mukofot: {t['reward']} ⭐"
        if t['photo'] != "none":
            await message.answer_photo(photo=t['photo'], caption=cap, reply_markup=kb.as_markup())
        else:
            await message.answer(text=cap, reply_markup=kb.as_markup())

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
            await callback.message.delete()
            await callback.answer(f"✅ +{t['reward']} ⭐ berildi!", show_alert=True)
        else:
            await callback.answer("❌ Kanalga a'zo bo'lmagansiz!", show_alert=True)
    except Exception:
        await callback.answer("❌ Xatolik: Bot ushbu kanalga admin qilinmagan yoki ID xato!", show_alert=True)

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
            await message.answer(f"✅ +{p['reward']} ⭐ qo'shildi!")
        else:
            await message.answer("❌ Limit tugagan yoki foydalangansiz.")
    else:
        await message.answer("❌ Noto'g'ri kod.")
    await state.clear()

# =====================================================================
# 9. STARS CHIQARISH VA TASDIQLASH
# =====================================================================
@dp.message(F.text == "📤 Stars chiqarish")
async def withdraw_menu(message: types.Message):
    u = init_user(message.from_user.id, message.from_user.first_name)
    kb = InlineKeyboardBuilder()
    for gid, g in gifts_db.items():
        kb.button(text=f"🎁 {g['name']} - {g['price']} ⭐", callback_data=f"with_{gid}")
    kb.adjust(1)
    
    await message.answer(
        f"📤 Sizning balansingiz: {u['stars']} ⭐\n(Minimal miqdor: 15 ⭐)\n\n"
        f"🎁 Quyidagi sovg'alardan birini tanlang:", reply_markup=kb.as_markup()
    )

@dp.callback_query(F.data.startswith("with_"))
async def request_withdraw(callback: types.CallbackQuery):
    gid = callback.data.split("_")[1]
    uid = callback.from_user.id
    u = users_db[uid]
    g = gifts_db.get(gid)
    
    if g and u["stars"] >= g["price"]:
        u["stars"] -= g["price"]
        kb = InlineKeyboardBuilder()
        kb.button(text="✅ Tasdiqlash", callback_data=f"ok_w_{uid}_{g['price']}")
        kb.button(text="❌ Rad etish", callback_data=f"no_w_{uid}_{g['price']}")
        
        await bot.send_message(
            chat_id=ADMIN_ID,
            text=f"🔔 <b>Yangi so'rov!</b>\n👤 Ism: {callback.from_user.full_name}\n🆔 {uid}\n🎁 {g['name']}\n💎 {g['price']} ⭐",
            parse_mode="HTML", reply_markup=kb.as_markup()
        )
        await callback.answer("✅ So'rov adminga yuborildi!", show_alert=True)
        # Edit user message nicely
        await callback.message.edit_text(callback.message.html_text + "\n\n⏳ <i>So'rov ko'rib chiqilmoqda...</i>", parse_mode="HTML")
    else:
        await callback.answer("❌ Balans yetarli emas!", show_alert=True)

@dp.callback_query(F.data.startswith("ok_w_"))
async def accept_w(callback: types.CallbackQuery):
    _, _, uid, price = callback.data.split("_")
    await callback.message.edit_text(callback.message.html_text + "\n\n✅ <b>Qabul qilindi!</b>", parse_mode="HTML")
    try:
        await bot.send_message(int(uid), "✅ <b>Tabriklaymiz!</b> Sizning sovg'a so'rovingiz admin tomonidan tasdiqlandi va amalga oshirildi!", parse_mode="HTML")
    except: pass

@dp.callback_query(F.data.startswith("no_w_"))
async def reject_w(callback: types.CallbackQuery):
    _, _, uid, price = callback.data.split("_")
    uid, price = int(uid), int(price)
    if uid in users_db: users_db[uid]["stars"] += price
    await callback.message.edit_text(callback.message.html_text + "\n\n❌ <b>Rad etildi!</b>", parse_mode="HTML")
    try:
        await bot.send_message(uid, "❌ Sovg'a so'rovingiz rad etildi. Stars balansingizga qaytarildi.")
    except: pass

# =====================================================================
# 10. MUKAMMAL ADMIN PANEL
# =====================================================================
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
    kb.button(text="💰 Balans", callback_data="adm_edit_bal")
    kb.button(text="📊 Statistika", callback_data="adm_get_stats")
    kb.adjust(2)
    await message.answer("👨‍💻 <b>Admin Boshqaruv Paneliga xush kelibsiz!</b>", parse_mode="HTML", reply_markup=kb.as_markup())

@dp.callback_query(F.data == "adm_get_stats")
async def a_stats(callback: types.CallbackQuery):
    await callback.answer(f"📊 Jami a'zolar: {len(users_db)} ta", show_alert=True)

@dp.callback_query(F.data == "adm_edit_ref")
async def a_ref1(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer(f"Hozirgi taklif mukofoti: {settings_db['ref_reward']} ⭐\nYangi narxni yozing:")
    await state.set_state(AdminState.waiting_for_ref_reward)

@dp.message(AdminState.waiting_for_ref_reward)
async def a_ref2(message: types.Message, state: FSMContext):
    if message.text.isdigit():
        settings_db["ref_reward"] = int(message.text)
        await message.answer(f"✅ Ref narxi o'zgardi: {message.text} ⭐")
    await state.clear()

# --- VAZIFA ---
@dp.callback_query(F.data == "adm_add_task")
async def a_task1(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("1/5: Rasm yuboring (yoki 'none' deb yozing):")
    await state.set_state(AdminState.waiting_for_task_photo)

@dp.message(AdminState.waiting_for_task_photo)
async def a_task2(message: types.Message, state: FSMContext):
    p_id = message.photo[-1].file_id if message.photo else "none"
    desc = message.caption if message.photo else message.text
    await state.update_data(p=p_id, d=desc)
    await message.answer("2/5: Kanal havolasini (URL) yuboring:")
    await state.set_state(AdminState.waiting_for_task_url)

@dp.message(AdminState.waiting_for_task_url)
async def a_task3(message: types.Message, state: FSMContext):
    await state.update_data(u=message.text)
    await message.answer("3/5: Kanal ID yoki Username bering:")
    await state.set_state(AdminState.waiting_for_task_chat_id)

@dp.message(AdminState.waiting_for_task_chat_id)
async def a_task4(message: types.Message, state: FSMContext):
    await state.update_data(c=message.text)
    await message.answer("4/5: Necha Stars mukofot berilsin?")
    await state.set_state(AdminState.waiting_for_task_reward)

@dp.message(AdminState.waiting_for_task_reward)
async def a_task5(message: types.Message, state: FSMContext):
    if message.text.isdigit():
        d = await state.get_data()
        tasks_db[str(len(tasks_db) + 1)] = {"photo": d['p'], "desc": d['d'], "url": d['u'], "chat_id": d['c'], "reward": int(message.text)}
        await message.answer("✅ Vazifa muvaffaqiyatli qo'shildi!")
    await state.clear()

@dp.callback_query(F.data == "adm_del_task")
async def a_deltask_list(callback: types.CallbackQuery):
    kb = InlineKeyboardBuilder()
    for tid, t in tasks_db.items(): kb.button(text=f"🗑 {t['desc'][:15]}...", callback_data=f"del_t_{tid}")
    kb.adjust(1)
    await callback.message.answer("O'chirish uchun tanlang:", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("del_t_"))
async def a_deltask_action(callback: types.CallbackQuery):
    tasks_db.pop(callback.data.split("_")[2], None)
    await callback.message.edit_text("✅ O'chirildi!")

# --- SOVG'A ---
@dp.callback_query(F.data == "adm_add_gift")
async def a_gift1(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("1/2: Sovg'a nomini yozing:")
    await state.set_state(AdminState.waiting_for_gift_name)

@dp.message(AdminState.waiting_for_gift_name)
async def a_gift2(message: types.Message, state: FSMContext):
    await state.update_data(n=message.text)
    await message.answer("2/2: Sovg'a narxini kiriting:")
    await state.set_state(AdminState.waiting_for_gift_price)

@dp.message(AdminState.waiting_for_gift_price)
async def a_gift3(message: types.Message, state: FSMContext):
    if message.text.isdigit():
        d = await state.get_data()
        gifts_db[str(len(gifts_db) + 1)] = {"name": d['n'], "price": int(message.text)}
        await message.answer("✅ Qo'shildi!")
    await state.clear()

@dp.callback_query(F.data == "adm_del_gift")
async def a_delgift_list(callback: types.CallbackQuery):
    kb = InlineKeyboardBuilder()
    for gid, g in gifts_db.items(): kb.button(text=f"🗑 {g['name']}", callback_data=f"del_g_{gid}")
    kb.adjust(1)
    await callback.message.answer("O'chirish uchun tanlang:", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("del_g_"))
async def a_delgift_action(callback: types.CallbackQuery):
    gifts_db.pop(callback.data.split("_")[2], None)
    await callback.message.edit_text("✅ O'chirildi!")

# --- PROMOKOD ---
@dp.callback_query(F.data == "adm_add_promo")
async def a_promo1(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("1/3: Promo matni:")
    await state.set_state(AdminState.waiting_for_promo_code)

@dp.message(AdminState.waiting_for_promo_code)
async def a_promo2(message: types.Message, state: FSMContext):
    await state.update_data(c=message.text)
    await message.answer("2/3: Mukofot (Stars):")
    await state.set_state(AdminState.waiting_for_promo_reward)

@dp.message(AdminState.waiting_for_promo_reward)
async def a_promo3(message: types.Message, state: FSMContext):
    await state.update_data(r=int(message.text))
    await message.answer("3/3: Necha kishi ishlata oladi?")
    await state.set_state(AdminState.waiting_for_promo_limit)

@dp.message(AdminState.waiting_for_promo_limit)
async def a_promo4(message: types.Message, state: FSMContext):
    d = await state.get_data()
    promocodes_db[d['c']] = {"reward": d['r'], "limit": int(message.text)}
    await message.answer("✅ Promokod faollashdi!")
    await state.clear()

# --- BALANS TAHRIRI ---
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
        await message.answer(f"✅ Balans tahrirlandi! Hozirgi: {users_db[d['i']]['stars']} ⭐")
    except:
        pass
    await state.clear()

# =====================================================================
# 11. ISHGA TUSHIRISH (ASYNC)
# =====================================================================
async def main():
    Thread(target=start_flask, daemon=True).start()
    logging.info("Bot tizimi ishga tushirildi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
