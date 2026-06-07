import os, asyncio, logging
from threading import Thread
from flask import Flask
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

BOT_TOKEN = "8788707258:AAGAsvxTBVYPqeT92qJDjqr0dgnsX8eZ2Fg"
ADMIN_ID, ADMIN_USERNAME = 8086545587, "pubgmobilepubgm86_coder"
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
app = Flask(__name__)

users_db, tasks_db, promocodes_db = {}, {}, {}
settings_db = {"ref_reward": 5}
gifts_db = {"1": {"name": "🧸 Ayiqcha (Mines)", "price": 15}, "2": {"name": "💎 Telegram Premium (1 oy)", "price": 250}}

def get_u(uid, name=""):
    if uid not in users_db: users_db[uid] = {"name": name, "stars": 0, "attempts": 10, "completed_tasks": [], "used_promos": []}
    return users_db[uid]

@app.route('/')
def index(): return "Bot Online!"

class AdminState(StatesGroup):
    t_p = State(); t_u = State(); t_c = State(); t_r = State()
    g_n = State(); g_p = State()
    p_c = State(); p_r = State(); p_l = State()
    r_r = State(); t_id = State(); b_v = State()

class UserState(StatesGroup): entering_promo = State()

def main_menu(uid):
    kb = ReplyKeyboardBuilder()
    for t in ["💎 Stars ishlash (O'yinlar)", "👤 Konchi Profili", "🏆 Top Konchilar", "ℹ️ Malumot / Qoidalar", "📋 Vazifalar (Free Stars)", "👥 Do'stlarni taklif qilish", "🎟 Promokod", "📤 Stars chiqarish"]: kb.button(text=t)
    if uid == ADMIN_ID: kb.button(text="⚙️ Admin Panel")
    return kb.adjust(2, 2, 2, 2, 1).as_markup(resize_keyboard=True)

def g_menu():
    return ReplyKeyboardBuilder().add(*[types.KeyboardButton(text=x) for x in ["🎯 Darts", "🎲 Kubik", "🏀 Basketbol", "⬅️ Orqaga"]]).adjust(3, 1).as_markup(resize_keyboard=True)

@dp.message(CommandStart())
async def cmd_start(m: types.Message):
    uid = m.from_user.id
    get_u(uid, m.from_user.first_name)
    args = m.text.split()
    if len(args) > 1 and args[1].isdigit():
        rid = int(args[1])
        if rid in users_db and rid != uid and rid not in users_db[uid]["used_promos"]:
            users_db[rid]["stars"] += settings_db["ref_reward"]
            users_db[uid]["used_promos"].append(rid)
            try: await bot.send_message(rid, f"🎉 <b>Yangi do'st!</b> Havolangiz orqali qo'shildi.\n+{settings_db['ref_reward']} ⭐", parse_mode="HTML")
            except: pass
    await m.answer(f"👋 Salom, {m.from_user.first_name}!\n\n🌟 <b>Stars Mines Free</b> — mutlaqo bepul Telegram Stars ishlash platformasiga xush kelibsiz.\nBu yerda siz turli o'yinlar orqali tekinga Stars qazib olishingiz mumkin.\n\n👇 Boshlash uchun pastdagi tugmalardan foydalaning!", parse_mode="HTML", reply_markup=main_menu(uid))

@dp.message(F.text == "👤 Konchi Profili")
async def profile(m: types.Message):
    u = get_u(m.from_user.id, m.from_user.first_name)
    await m.answer(f"👤 Profil:\n🆔 {m.from_user.id}\n💎 Balans: {u['stars']} ⭐\n⚡ Energiya: {u['attempts']} marta")

@dp.message(F.text == "ℹ️ Malumot / Qoidalar")
async def rules(m: types.Message):
    await m.answer("ℹ️ <b>Stars Mines Free Qoidalari:</b>\n\nBotingiz orqali tekinga Stars ishlash juda oson!\n\n1️⃣ 💎 Stars ishlash tugmasini bosing.\n2️⃣ Botga emojilardan birini yuboring:\n  🎯 (Darts) - O'q aniq markazga tegsa (2 Star)\n  🎲 (Kubik) - Agar 6 raqami tushsa (2 Star)\n  🏀 (Basketbol) - Koptok savatga tushsa (2 Star)\n\n3️⃣ Har bir foydalanuvchiga kuniga 10 ta bepul energiya beriladi.\n4️⃣ Yig'ilgan Stars'lar to'g'ridan-to'g'ri balansingizga qo'shilib boradi!", parse_mode="HTML")

@dp.message(F.text == "🏆 Top Konchilar")
async def top_m(m: types.Message):
    if not users_db: return await m.answer("🏆 Hali hech kim yo'q.")
    top = sorted(users_db.items(), key=lambda x: x[1]['stars'], reverse=True)[:5]
    txt = "🏆 <b>Top-5 Stars Konchilari:</b>\n\n" + "\n".join([f"{i}. {d['name']} — {d['stars']} ⭐" for i, (uid, d) in enumerate(top, 1)])
    await m.answer(txt, parse_mode="HTML")

@dp.message(F.text == "👥 Do'stlarni taklif qilish")
async def ref(m: types.Message):
    me = await bot.get_me()
    await m.answer(f"👥 <b>Do'stlarni taklif qiling!</b>\n\n🔗 Havolangiz: <code>https://t.me/{me.username}?start={m.from_user.id}</code>\n\nHar bir taklif uchun mukofot: <b>{settings_db['ref_reward']} ⭐</b>", parse_mode="HTML")

@dp.message(F.text == "💎 Stars ishlash (O'yinlar)")
async def g_start(m: types.Message): await m.answer("🎮 Menga stikerlardan birini yuboring:\n🎯 (Darts), 🎲 (Kubik) yoki 🏀 (Basketbol)", reply_markup=g_menu())

@dp.message(F.text.in_(["🎯 Darts", "🎲 Kubik", "🏀 Basketbol"]))
async def play(m: types.Message):
    u = get_u(m.from_user.id, m.from_user.first_name)
    if u["attempts"] <= 0: return await m.answer("⚡ Bugungi energiya tugadi!")
    u["attempts"] -= 1; emo = m.text.split()[0]; msg = await m.answer_dice(emoji=emo); await asyncio.sleep(2.5)
    win = (emo in ["🎯", "🎲"] and msg.dice.value == 6) or (emo == "🏀" and msg.dice.value in [4, 5])
    if win: u["stars"] += 2; await m.answer(f"🎉 <b>Yutuq!</b> +2 ⭐\n⚡ Qolgan energiya: {u['attempts']}", parse_mode="HTML")
    else: await m.answer(f"❌ <b>O'xshamadi.</b> Natija: {msg.dice.value}\n⚡ Energiya: {u['attempts']}", parse_mode="HTML")

@dp.message(F.text == "⬅️ Orqaga")
async def back(m: types.Message): await m.answer("Asosiy menyu:", reply_markup=main_menu(m.from_user.id))

@dp.message(F.text == "📋 Vazifalar (Free Stars)")
async def tasks(m: types.Message):
    u = get_u(m.from_user.id, m.from_user.first_name)
    active = [tid for tid in tasks_db if tid not in u["completed_tasks"]]
    if not active: return await m.answer("Barcha vazifalar bajarilgan!")
    for tid in active:
        t = tasks_db[tid]; kb = InlineKeyboardBuilder().button(text="🔗 Kanal", url=t['url']).button(text="✅ Tekshirish", callback_data=f"chk_{tid}").adjust(1).as_markup()
        cap = f"📝 {t['desc']}\n💎 Mukofot: {t['reward']} ⭐"
        if t['photo'] != "none": await m.answer_photo(photo=t['photo'], caption=cap, reply_markup=kb)
        else: await m.answer(text=cap, reply_markup=kb)

@dp.callback_query(F.data.startswith("chk_"))
async def chk_t(c: types.CallbackQuery):
    tid = c.data.split("_")[1]; u = get_u(c.from_user.id, c.from_user.first_name); t = tasks_db.get(tid)
    if not t: return await c.answer("Vazifa o'chirilgan!", show_alert=True)
    if tid in u["completed_tasks"]: return await c.answer("Bajarilgan!", show_alert=True)
    try:
        m = await bot.get_chat_member(chat_id=t['chat_id'], user_id=c.from_user.id)
        if m.status in ['member', 'administrator', 'creator']:
            u["stars"] += t['reward']; u["completed_tasks"].append(tid); await c.message.delete(); await c.answer(f"✅ +{t['reward']} ⭐ berildi!", show_alert=True)
        else: await c.answer("❌ Kanalga a'zo bo'lmagansiz!", show_alert=True)
    except: await c.answer("❌ Xatolik: Bot ushbu kanalga admin qilinmagan yoki ID xato!", show_alert=True)

@dp.message(F.text == "🎟 Promokod")
async def promo(m: types.Message, s: FSMContext): await m.answer("🎟 Promokodni kiriting:"); await s.set_state(UserState.entering_promo)

@dp.message(UserState.entering_promo)
async def chk_promo(m: types.Message, s: FSMContext):
    code = m.text.strip(); u = get_u(m.from_user.id, m.from_user.first_name)
    if code in promocodes_db:
        p = promocodes_db[code]
        if p["limit"] > 0 and code not in u["used_promos"]:
            u["stars"] += p["reward"]; u["used_promos"].append(code); p["limit"] -= 1; await m.answer(f"✅ +{p['reward']} ⭐ qo'shildi!")
        else: await m.answer("❌ Limit tugagan yoki foydalangansiz.")
    else: await m.answer("❌ Noto'g'ri kod.")
    await s.clear()

@dp.message(F.text == "📤 Stars chiqarish")
async def withdraw(m: types.Message):
    u = get_u(m.from_user.id, m.from_user.first_name); kb = InlineKeyboardBuilder()
    for gid, g in gifts_db.items(): kb.button(text=f"🎁 {g['name']} - {g['price']} ⭐", callback_data=f"w_{gid}")
    await m.answer(f"📤 Sizning balansingiz: {u['stars']} ⭐\n(Minimal miqdor: 15 ⭐)\n\n🎁 Quyidagi sovg'alardan birini tanlang:", reply_markup=kb.adjust(1).as_markup())

@dp.callback_query(F.data.startswith("w_"))
async def req_w(c: types.CallbackQuery):
    gid, uid = c.data.split("_")[1], c.from_user.id; u, g = users_db[uid], gifts_db.get(gid)
    if g and u["stars"] >= g["price"]:
        u["stars"] -= g["price"]; kb = InlineKeyboardBuilder().button(text="✅ Tasdiqlash", callback_data=f"ok_{uid}_{g['price']}").button(text="❌ Rad etish", callback_data=f"no_{uid}_{g['price']}").adjust(2).as_markup()
        await bot.send_message(ADMIN_ID, f"🔔 <b>Yangi so'rov!</b>\n👤 Ism: {c.from_user.full_name}\n🆔 {uid}\n🎁 {g['name']}\n💎 {g['price']} ⭐", parse_mode="HTML", reply_markup=kb)
        await c.answer("✅ So'rov adminga yuborildi!", show_alert=True); await c.message.edit_text(c.message.html_text + "\n\n⏳ <i>So'rov ko'rib chiqilmoqda...</i>", parse_mode="HTML")
    else: await c.answer("❌ Balans yetarli emas!", show_alert=True)

@dp.callback_query(F.data.startswith("ok_"))
async def acc_w(c: types.CallbackQuery):
    _, uid, price = c.data.split("_"); await c.message.edit_text(c.message.html_text + "\n\n✅ <b>Qabul qilindi!</b>", parse_mode="HTML")
    try: await bot.send_message(int(uid), "✅ <b>Tabriklaymiz!</b> Sizning sovg'a so'rovingiz admin tomonidan tasdiqlandi va amalga oshirildi!", parse_mode="HTML")
    except: pass

@dp.callback_query(F.data.startswith("no_"))
async def rej_w(c: types.CallbackQuery):
    _, uid, price = c.data.split("_"); uid, price = int(uid), int(price)
    if uid in users_db: users_db[uid]["stars"] += price
    await c.message.edit_text(c.message.html_text + "\n\n❌ <b>Rad etildi!</b>", parse_mode="HTML")
    try: await bot.send_message(uid, "❌ Sovg'a so'rovingiz rad etildi. Stars balansingizga qaytarildi.")
    except: pass

@dp.message(F.text == "⚙️ Admin Panel")
async def a_panel(m: types.Message):
    if m.from_user.id != ADMIN_ID: return
    kb = InlineKeyboardBuilder()
    for k, v in {"➕ Vazifa": "a_at", "🗑 Vazifa": "a_dt", "🎁 Sovg'a": "a_ag", "🗑 Sovg'a": "a_dg", "🎟 Promo": "a_ap", "🔗 Ref Narx": "a_er", "💰 Balans": "a_eb", "📊 Statistika": "a_gs"}.items(): kb.button(text=k, callback_data=v)
    await m.answer("👨‍💻 <b>Admin Boshqaruv Paneliga xush kelibsiz!</b>", parse_mode="HTML", reply_markup=kb.adjust(2).as_markup())

@dp.callback_query(F.data == "a_gs")
async def a_stats(c: types.CallbackQuery): await c.answer(f"📊 Jami a'zolar: {len(users_db)} ta", show_alert=True)

@dp.callback_query(F.data == "a_er")
async def a_ref1(c: types.CallbackQuery, s: FSMContext): await c.message.answer(f"Hozirgi taklif mukofoti: {settings_db['ref_reward']} ⭐\nYangi narxni yozing:"); await s.set_state(AdminState.r_r)

@dp.message(AdminState.r_r)
async def a_ref2(m: types.Message, s: FSMContext):
    if m.text.isdigit(): settings_db["ref_reward"] = int(m.text); await m.answer(f"✅ Ref narxi o'zgardi: {m.text} ⭐")
    await s.clear()

@dp.callback_query(F.data == "a_at")
async def a_t1(c: types.CallbackQuery, s: FSMContext): await c.message.answer("1/5: Rasm yuboring (yoki 'none' deb yozing):"); await s.set_state(AdminState.t_p)

@dp.message(AdminState.t_p)
async def a_t2(m: types.Message, s: FSMContext):
    p = m.photo[-1].file_id if m.photo else "none"; d = m.caption if m.photo else m.text
    await s.update_data(p=p, d=d); await m.answer("2/5: Kanal havolasini (URL) yuboring:"); await s.set_state(AdminState.t_u)

@dp.message(AdminState.t_u)
async def a_t3(m: types.Message, s: FSMContext): await s.update_data(u=m.text); await m.answer("3/5: Kanal ID yoki Username bering:"); await s.set_state(AdminState.t_c)

@dp.message(AdminState.t_c)
async def a_t4(m: types.Message, s: FSMContext): await s.update_data(c=m.text); await m.answer("4/5: Necha Stars mukofot berilsin?"); await s.set_state(AdminState.t_r)

@dp.message(AdminState.t_r)
async def a_t5(m: types.Message, s: FSMContext):
    if m.text.isdigit():
        d = await s.get_data(); tasks_db[str(len(tasks_db) + 1)] = {"photo": d['p'], "desc": d['d'], "url": d['u'], "chat_id": d['c'], "reward": int(m.text)}
        await m.answer("✅ Vazifa muvaffaqiyatli qo'shildi!")
    await s.clear()

@dp.callback_query(F.data == "a_dt")
async def a_dt_l(c: types.CallbackQuery):
    kb = InlineKeyboardBuilder()
    for tid, t in tasks_db.items(): kb.button(text=f"🗑 {t['desc'][:15]}...", callback_data=f"dt_{tid}")
    await c.message.answer("O'chirish uchun tanlang:", reply_markup=kb.adjust(1).as_markup())

@dp.callback_query(F.data.startswith("dt_"))
async def a_dt_a(c: types.CallbackQuery): tasks_db.pop(c.data.split("_")[1], None); await c.message.edit_text("✅ O'chirildi!")

@dp.callback_query(F.data == "a_ag")
async def a_g1(c: types.CallbackQuery, s: FSMContext): await c.message.answer("1/2: Sovg'a nomini yozing:"); await s.set_state(AdminState.g_n)

@dp.message(AdminState.g_n)
async def a_g2(m: types.Message, s: FSMContext): await s.update_data(n=m.text); await m.answer("2/2: Sovg'a narxini kiriting:"); await s.set_state(AdminState.g_p)

@dp.message(AdminState.g_p)
async def a_g3(m: types.Message, s: FSMContext):
    if m.text.isdigit():
        d = await s.get_data(); gifts_db[str(len(gifts_db) + 1)] = {"name": d['n'], "price": int(m.text)}
        await m.answer("✅ Qo'shildi!")
    await s.clear()

@dp.callback_query(F.data == "a_dg")
async def a_dg_l(c: types.CallbackQuery):
    kb = InlineKeyboardBuilder()
    for gid, g in gifts_db.items(): kb.button(text=f"🗑 {g['name']}", callback_data=f"dg_{gid}")
    await c.message.answer("O'chirish uchun tanlang:", reply_markup=kb.adjust(1).as_markup())

@dp.callback_query(F.data.startswith("dg_"))
async def a_dg_a(c: types.CallbackQuery): gifts_db.pop(c.data.split("_")[1], None); await c.message.edit_text("✅ O'chirildi!")

@dp.callback_query(F.data == "a_ap")
async def a_p1(c: types.CallbackQuery, s: FSMContext): await c.message.answer("1/3: Promo matni:"); await s.set_state(AdminState.p_c)

@dp.message(AdminState.p_c)
async def a_p2(m: types.Message, s: FSMContext): await s.update_data(c=m.text); await m.answer("2/3: Mukofot (Stars):"); await s.set_state(AdminState.p_r)

@dp.message(AdminState.p_r)
async def a_p3(m: types.Message, s: FSMContext): await s.update_data(r=int(m.text)); await m.answer("3/3: Necha kishi ishlata oladi?"); await s.set_state(AdminState.p_l)

@dp.message(AdminState.p_l)
async def a_p4(m: types.Message, s: FSMContext):
    d = await s.get_data(); promocodes_db[d['c']] = {"reward": d['r'], "limit": int(m.text)}; await m.answer("✅ Promokod faollashdi!"); await s.clear()

@dp.callback_query(F.data == "a_eb")
async def a_b1(c: types.CallbackQuery, s: FSMContext): await c.message.answer("Foydalanuvchi ID raqamini kiriting:"); await s.set_state(AdminState.t_id)

@dp.message(AdminState.t_id)
async def a_b2(m: types.Message, s: FSMContext):
    if m.text.isdigit() and int(m.text) in users_db: await s.update_data(i=int(m.text)); await m.answer("Qancha Stars qo'shmoqchisiz (Yoki ayirish uchun -10):"); await s.set_state(AdminState.b_v)
    else: await m.answer("❌ ID topilmadi."); await s.clear()

@dp.message(AdminState.b_v)
async def a_b3(m: types.Message, s: FSMContext):
    try: d = await s.get_data(); users_db[d['i']]['stars'] = max(0, users_db[d['i']]['stars'] + int(m.text)); await m.answer(f"✅ Balans tahrirlandi! Hozirgi: {users_db[d['i']]['stars']} ⭐")
    except: pass
    await s.clear()

async def main():
    Thread(target=lambda: app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000))), daemon=True).start()
    await dp.start_polling(bot)

if __name__ == "__main__": asyncio.run(main())
