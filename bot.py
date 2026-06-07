import os, logging, asyncio
from threading import Thread
from flask import Flask
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

# ---- SOZLAMALAR ----
BOT_TOKEN, PORT, ADMIN_ID = "8788707258:AAGAsvxTBVYPqeT92qJDjqr0dgnsX8eZ2Fg", int(os.environ.get("PORT", 10000)), 8086545587
logging.basicConfig(level=logging.INFO)

bot, dp = Bot(token=BOT_TOKEN), Dispatcher(storage=MemoryStorage())
app = Flask(__name__)

# ---- BAZALAR ----
users_db, tasks_db, promocodes_db = {}, {}, {}
gifts_db = {"1": {"name": "🧸 Ayiqcha", "price": 15}, "2": {"name": "💎 TG Premium (1 oy)", "price": 250}}

# ---- SERVER ----
@app.route('/')
def home(): return "Stars Mines Free boti 24/7 ishlamoqda!"

# ---- FSM HOLATLARI ----
class AdminState(StatesGroup):
    t_photo, t_url, t_reward = State(), State(), State()
    g_name, g_price = State(), State()
    p_code, p_reward, p_limit = State(), State(), State()
    a_id, a_amount = State(), State()
class UserPromo(StatesGroup): code = State()

# ---- KLAVIATURALAR ----
def main_menu(uid):
    btns = ["💎 Stars ishlash (O'yinlar)", "📋 Vazifalar (Free Stars)", "👤 Profil", "📤 Stars chiqarish", "🎟 Promokod", "🏆 Top Konchilar", "ℹ️ Malumot / Qoidalar"]
    if uid == ADMIN_ID: btns.append("⚙️ Admin Panel")
    b = ReplyKeyboardBuilder()
    [b.add(types.KeyboardButton(text=t)) for t in btns]
    return b.adjust(2, 2, 2, 2, 1).as_markup(resize_keyboard=True)

def inline_btn(btn_data, adjust_val=1):
    b = InlineKeyboardBuilder()
    [b.button(text=text, **( {"url": cb} if cb.startswith("http") else {"callback_data": cb} )) for text, cb in btn_data]
    return b.adjust(adjust_val).as_markup()

# ---- START & ASOSIY BO'LIMLAR ----
@dp.message(CommandStart())
async def start(m: types.Message):
    if m.from_user.id not in users_db:
        users_db[m.from_user.id] = {"name": m.from_user.first_name, "stars": 0, "attempts": 10, "tasks": [], "promos": []}
    await m.answer(f"👋 **Salom, {m.from_user.first_name}!**\n🌟 **Stars Mines Free**ga xush kelibsiz!", parse_mode="Markdown", reply_markup=main_menu(m.from_user.id))

@dp.message(F.text == "👤 Profil")
async def profile(m: types.Message):
    u = users_db.get(m.from_user.id, {"stars": 0, "attempts": 0})
    await m.answer(f"👤 **Profil:**\n🆔 `{m.from_user.id}`\n💎 Balans: **{u['stars']} ⭐**\n⚡ Energiya: **{u['attempts']}** marta", parse_mode="Markdown")

@dp.message(F.text == "ℹ️ Malumot / Qoidalar")
async def rules(m: types.Message):
    await m.answer("ℹ️ Botda vazifa, oʻyin va promokod orqali Stars ishlaysiz (Min. 15⭐).\n⚠️ **Qoidalar:** Nakrutka qat'iyan man etiladi, hisob bloklanadi!", parse_mode="Markdown")

@dp.message(F.text == "🏆 Top Konchilar")
async def leaders(m: types.Message):
    t = "🏆 **Top-5 Konchilar:**\n\n" + "".join([f"{i}. {d['name']} — {d['stars']} ⭐\n" for i, (k, d) in enumerate(sorted(users_db.items(), key=lambda x: x[1]['stars'], reverse=True)[:5], 1)]) if users_db else "Bo'sh!"
    await m.answer(t, parse_mode="Markdown")

# ---- VAZIFALAR ----
@dp.message(F.text == "📋 Vazifalar (Free Stars)")
async def tasks(m: types.Message):
    avail = [t for t in tasks_db if t not in users_db.get(m.from_user.id, {}).get("tasks", [])]
    if not avail: return await m.answer("🎉 Barcha vazifalar bajarilgan yoki yo'q.")
    for t_id in avail:
        t = tasks_db[t_id]
        cap = f"📝 **Vazifa:** {t['desc']}\n💎 **Mukofot:** {t['reward']} ⭐"
        rm = inline_btn([("🔗 Kirish", t['url']), ("✅ Bajardim", f"chk_t_{t_id}")])
        await m.answer_photo(t['photo'], caption=cap, parse_mode="Markdown", reply_markup=rm) if t.get('photo') != "none" else await m.answer(cap, parse_mode="Markdown", reply_markup=rm)

@dp.callback_query(F.data.startswith("chk_t_"))
async def chk_task(c: types.CallbackQuery):
    tid, uid = c.data.split("_")[2], c.from_user.id
    u = users_db.get(uid)
    if tid in tasks_db and tid not in u.get("tasks", []):
        r = tasks_db[tid]['reward']
        u["stars"] += r; u.setdefault("tasks", []).append(tid)
        try: await c.message.delete()
        except: pass
        await c.answer(f"✅ +{r} Stars!", show_alert=True)
        await bot.send_message(uid, f"💎 Balansingizga {r} Stars qo'shildi!")
    else: await c.answer("Avval bajargansiz!", show_alert=True)

# ---- PROMOKOD ----
@dp.message(F.text == "🎟 Promokod")
async def pr_st(m: types.Message, state: FSMContext): await m.answer("🎟 Promokodni kiriting:"), await state.set_state(UserPromo.code)
@dp.message(UserPromo.code)
async def pr_ap(m: types.Message, state: FSMContext):
    c, u = m.text.strip(), users_db.get(m.from_user.id)
    if c in promocodes_db and promocodes_db[c]["limit"] > 0 and c not in u.get("promos", []):
        u["stars"] += promocodes_db[c]["reward"]; u.setdefault("promos", []).append(c); promocodes_db[c]["limit"] -= 1
        await m.answer(f"✅ Qabul qilindi! +{promocodes_db[c]['reward']} ⭐")
    else: await m.answer("❌ Xato, limit tugagan yoki ishlatilgan.")
    await state.clear()

# ---- O'YINLAR ----
@dp.message(F.text == "💎 Stars ishlash (O'yinlar)")
async def p_game(m: types.Message): await m.answer("🎮 Stikerlardan birini yuboring:\n🎯 (Darts), 🎲 (Kubik) yoki 🏀 (Basketbol)")
@dp.message(F.dice)
async def dice(m: types.Message):
    if m.dice.emoji not in ["🎯", "🎲", "🏀"] or m.from_user.id not in users_db: return
    u = users_db[m.from_user.id]
    if u["attempts"] <= 0: return await m.answer("😔 Energiya tugadi.")
    u["attempts"] -= 1; await asyncio.sleep(2.5)
    win = (m.dice.value == 6 and m.dice.emoji in ["🎯", "🎲"]) or (m.dice.emoji == "🏀" and m.dice.value in [4, 5])
    if win: u["stars"] += 1
    await m.answer(f"🎉 **YUTUQ!** +1 ⭐\n⚡ Energiya: {u['attempts']}" if win else f"❌ Nishonga tegmadi.\n⚡ Energiya: {u['attempts']}", parse_mode="Markdown")

# ---- CHIQARISH ----
@dp.message(F.text == "📤 Stars chiqarish")
async def w_draw(m: types.Message):
    rm = inline_btn([(f"{g['name']} - {g['price']} ⭐", f"buy_{gid}") for gid, g in gifts_db.items()])
    await m.answer(f"📤 Balans: **{users_db.get(m.from_user.id, {}).get('stars', 0)} ⭐**\n(Min: 15)\n\n🎁 Sovg'ani tanlang:", parse_mode="Markdown", reply_markup=rm)

@dp.callback_query(F.data.startswith("buy_"))
async def w_buy(c: types.CallbackQuery):
    gid, uid, u = c.data.split("_")[1], c.from_user.id, users_db.get(c.from_user.id)
    if gid in gifts_db:
        g = gifts_db[gid]
        if u["stars"] < 15 or u["stars"] < g["price"]: return await c.answer("❌ Balans yetarli emas!", show_alert=True)
        u["stars"] -= g["price"]
        await bot.send_message(ADMIN_ID, f"🔔 **Sovg'a so'rovi!**\n👤 {c.from_user.full_name} (`{uid}`)\n🎁 {g['name']}\n💎 {g['price']} ⭐", parse_mode="Markdown")
        await c.answer("✅ Adminga yuborildi!", show_alert=True)

# ================= ADMIN PANEL =================
@dp.message(F.text == "⚙️ Admin Panel")
async def adm_p(m: types.Message):
    if m.from_user.id != ADMIN_ID: return
    btns = [("➕ Vazifa", "a_t_add"), ("➖ Vazifa", "a_t_del"), ("🎁 Sovg'a", "a_g_add"), ("🗑 Sovg'a", "a_g_del"), ("🎟 Promo", "a_p_add"), ("💰 Hisob", "a_acc"), ("📊 Stat", "a_stat")]
    await m.answer("👨‍💻 **Admin Panel**", parse_mode="Markdown", reply_markup=inline_btn(btns, 2))

@dp.callback_query(F.data == "a_stat")
async def a_stat(c: types.CallbackQuery): await c.answer(f"📊 Foydalanuvchilar: {len(users_db)}", show_alert=True)

# Admin: Task
@dp.callback_query(F.data == "a_t_add")
async def t_a1(c: types.CallbackQuery, state: FSMContext): await c.message.answer("1️⃣ Rasm yuboring (yoki matn):"), await state.set_state(AdminState.t_photo)
@dp.message(AdminState.t_photo)
async def t_a2(m: types.Message, state: FSMContext): await state.update_data(p=m.photo[-1].file_id if m.photo else "none", d=m.caption or m.text), await m.answer("2️⃣ URL:"), await state.set_state(AdminState.t_url)
@dp.message(AdminState.t_url)
async def t_a3(m: types.Message, state: FSMContext): await state.update_data(u=m.text), await m.answer("3️⃣ Mukofot (⭐):"), await state.set_state(AdminState.t_reward)
@dp.message(AdminState.t_reward)
async def t_a4(m: types.Message, state: FSMContext): 
    d = await state.get_data(); tasks_db[str(len(tasks_db)+1)] = {"photo": d['p'], "desc": d['d'], "url": d['u'], "reward": int(m.text)}
    await m.answer("✅ Vazifa qo'shildi!"); await state.clear()
@dp.callback_query(F.data == "a_t_del")
async def t_d1(c: types.CallbackQuery): await c.message.answer("🗑 Vazifani tanlang:", reply_markup=inline_btn([(f"🗑 {t['desc']}", f"d_t_{tid}") for tid, t in tasks_db.items()]))
@dp.callback_query(F.data.startswith("d_t_"))
async def t_d2(c: types.CallbackQuery): tasks_db.pop(c.data.split("_")[2], None); await c.message.edit_text("✅ O'chirildi!")

# Admin: Gift
@dp.callback_query(F.data == "a_g_add")
async def g_a1(c: types.CallbackQuery, state: FSMContext): await c.message.answer("1️⃣ Sovg'a nomi:"), await state.set_state(AdminState.g_name)
@dp.message(AdminState.g_name)
async def g_a2(m: types.Message, state: FSMContext): await state.update_data(n=m.text), await m.answer("2️⃣ Narxi (⭐):"), await state.set_state(AdminState.g_price)
@dp.message(AdminState.g_price)
async def g_a3(m: types.Message, state: FSMContext): gifts_db[str(len(gifts_db)+1)] = {"name": (await state.get_data())['n'], "price": int(m.text)}; await m.answer("✅ Qo'shildi!"); await state.clear()
@dp.callback_query(F.data == "a_g_del")
async def g_d1(c: types.CallbackQuery): await c.message.answer("🗑 Sovg'ani tanlang:", reply_markup=inline_btn([(f"🗑 {g['name']}", f"d_g_{gid}") for gid, g in gifts_db.items()]))
@dp.callback_query(F.data.startswith("d_g_"))
async def g_d2(c: types.CallbackQuery): gifts_db.pop(c.data.split("_")[2], None); await c.message.edit_text("✅ O'chirildi!")

# Admin: Promo
@dp.callback_query(F.data == "a_p_add")
async def p_a1(c: types.CallbackQuery, state: FSMContext): await c.message.answer("🎟 Kod matni:"), await state.set_state(AdminState.p_code)
@dp.message(AdminState.p_code)
async def p_a2(m: types.Message, state: FSMContext): await state.update_data(c=m.text.strip()), await m.answer("💎 Mukofot (⭐):"), await state.set_state(AdminState.p_reward)
@dp.message(AdminState.p_reward)
async def p_a3(m: types.Message, state: FSMContext): await state.update_data(r=int(m.text)), await m.answer("👥 Limit:"), await state.set_state(AdminState.p_limit)
@dp.message(AdminState.p_limit)
async def p_a4(m: types.Message, state: FSMContext):
    d = await state.get_data(); promocodes_db[d['c']] = {"reward": d['r'], "limit": int(m.text)}
    await m.answer(f"✅ Promo yaratildi: `{d['c']}`", parse_mode="Markdown"); await state.clear()

# Admin: Account
@dp.callback_query(F.data == "a_acc")
async def ac_1(c: types.CallbackQuery, state: FSMContext): await c.message.answer("👤 Foydalanuvchi IDsi:"), await state.set_state(AdminState.a_id)
@dp.message(AdminState.a_id)
async def ac_2(m: types.Message, state: FSMContext):
    if int(m.text) not in users_db: return await m.answer("❌ Topilmadi."), await state.clear()
    await state.update_data(id=int(m.text)), await m.answer(f"Balans: {users_db[int(m.text)]['stars']}⭐\nQo'shish/Ayirish (masalan: 50 yoki -20):"), await state.set_state(AdminState.a_amount)
@dp.message(AdminState.a_amount)
async def ac_3(m: types.Message, state: FSMContext):
    uid = (await state.get_data())['id']; users_db[uid]['stars'] = max(0, users_db[uid]['stars'] + int(m.text))
    await m.answer(f"✅ Yangi balans: {users_db[uid]['stars']} ⭐")
    await bot.send_message(uid, f"🔔 Admin hisobingizni o'zgartirdi.\nYangi balans: **{users_db[uid]['stars']} ⭐**", parse_mode="Markdown"); await state.clear()

# ---- ISHGA TUSHIRISH ----
async def main():
    Thread(target=lambda: app.run(host="0.0.0.0", port=PORT), daemon=True).start()
    await dp.start_polling(bot)

if __name__ == "__main__": asyncio.run(main())
    
