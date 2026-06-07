import os, asyncio
from threading import Thread
from flask import Flask
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

# 1. SOZLAMALAR VA BAZA
BOT_TOKEN = "8788707258:AAGAsvxTBVYPqeT92qJDjqr0dgnsX8eZ2Fg"
PORT = int(os.environ.get("PORT", 10000))
ADMIN_ID = 8086545587

bot, dp, app = Bot(token=BOT_TOKEN), Dispatcher(storage=MemoryStorage()), Flask(__name__)
users_db, tasks_db, promos_db = {}, {}, {}
settings = {"ref": 5}
gifts = {"1": {"n": "🧸 Ayiqcha", "p": 15}, "2": {"n": "💎 TG Premium", "p": 250}}

# 2. SERVER (RENDER)
@app.route('/')
def home(): return "Bot faol"
def run_flask(): app.run(host="0.0.0.0", port=PORT)

class Adm(StatesGroup): add_t, add_p = State(), State()
class Usr(StatesGroup): promo = State()

def kb(*btns):
    b = ReplyKeyboardBuilder()
    [b.add(types.KeyboardButton(text=t)) for t in btns]
    return b.adjust(2).as_markup(resize_keyboard=True)

def ikb(btns):
    b = InlineKeyboardBuilder()
    [b.button(text=t, callback_data=d) for t, d in btns]
    return b.adjust(1).as_markup()

m_btns = ["💎 O'yinlar", "📋 Vazifalar", "👥 Do'stlar", "🎟 Promo", "👤 Profil", "📤 Chiqarish"]
if ADMIN_ID: m_btns.append("⚙️ Admin")

# 3. ASOSIY MENYU VA REFERAL
@dp.message(CommandStart())
async def start(m: types.Message):
    u = m.from_user.id
    if u not in users_db:
        users_db[u] = {"n": m.from_user.first_name, "s": 0, "a": 10, "t": [], "p": []}
        args = m.text.split()
        if len(args) > 1 and args[1].isdigit():
            r = int(args[1])
            if r in users_db and r != u:
                users_db[r]["s"] += settings["ref"]
                try: await bot.send_message(r, f"🎉 Do'stingiz kirdi! +{settings['ref']}⭐")
                except: pass
    await m.answer("👋 Bosh menyu:", reply_markup=kb(*m_btns))

@dp.message(F.text == "👥 Do'stlar")
async def ref(m: types.Message):
    un = (await bot.get_me()).username
    await m.answer(f"👥 Sizning link:\n`https://t.me/{un}?start={m.from_user.id}`\n\nHar bir do'st: +{settings['ref']}⭐", parse_mode="Markdown")

@dp.message(F.text == "👤 Profil")
async def prof(m: types.Message):
    u = users_db.get(m.from_user.id, {"s": 0, "a": 10})
    await m.answer(f"👤 ID: `{m.from_user.id}`\n💎 Balans: {u['s']}⭐\n⚡ Energiya: {u['a']}", parse_mode="Markdown")

# 4. VAZIFALAR TIZIMI
@dp.message(F.text == "📋 Vazifalar")
async def tasks(m: types.Message):
    u = users_db.get(m.from_user.id, {"t": []})
    av = [i for i in tasks_db if i not in u.get("t", [])]
    if not av: return await m.answer("🎉 Barcha vazifalar bajarilgan!")
    for i in av:
        t = tasks_db[i]
        await m.answer(f"📝 {t['d']} | 💎 {t['r']}⭐", reply_markup=ikb([("🔗 Kirish", t['u']), ("✅ Tekshirish", f"chk_{i}")]))

@dp.callback_query(F.data.startswith("chk_"))
async def chk_t(c: types.CallbackQuery):
    i = c.data.split("_")[1]
    u, t = users_db.get(c.from_user.id), tasks_db.get(i)
    if not t: return await c.answer("❌ O'chirilgan!", show_alert=True)
    try:
        mem = await bot.get_chat_member(t['c'], c.from_user.id)
        if mem.status not in ['member', 'administrator', 'creator']: raise Exception
        u["s"] += t['r']; u["t"].append(i)
        await c.message.delete()
        await c.answer(f"✅ +{t['r']}⭐", show_alert=True)
    except: await c.answer("❌ Obuna bo'lmagansiz yoki xatolik!", show_alert=True)

# 5. O'YINLAR
@dp.message(F.text == "💎 O'yinlar")
async def games(m: types.Message):
    await m.answer("🎮 Tanlang:", reply_markup=kb("🎯 Darts", "🎲 Kubik", "🏀 Basketbol", "⬅️ Orqaga"))

@dp.message(F.text.in_(["🎯 Darts", "🎲 Kubik", "🏀 Basketbol"]))
async def play(m: types.Message):
    u = users_db.get(m.from_user.id)
    if u["a"] <= 0: return await m.answer("😔 Energiya tugagan!")
    u["a"] -= 1; emo = m.text.split()[0]
    d = await m.answer_dice(emo); await asyncio.sleep(2.5)
    win = (emo in ["🎯", "🎲"] and d.dice.value == 6) or (emo == "🏀" and d.dice.value in [4, 5])
    if win: u["s"] += 1
    await m.answer(f"{'🎉 YUTDINGIZ! +1⭐' if win else '❌ Omadsiz.'}\n⚡ Qoldi: {u['a']}")

@dp.message(F.text == "⬅️ Orqaga")
async def back(m: types.Message): await start(m)

# 6. PROMOKOD TIZIMI
@dp.message(F.text == "🎟 Promo")
async def prm(m: types.Message, state: FSMContext):
    await m.answer("🎟 Kodni yozing:"); await state.set_state(Usr.promo)

@dp.message(Usr.promo)
async def prm_chk(m: types.Message, state: FSMContext):
    c, u = m.text.strip(), users_db.get(m.from_user.id)
    p = promos_db.get(c)
    if p and p["l"] > 0 and c not in u.get("p", []):
        u["s"] += p["r"]; u.setdefault("p", []).append(c); p["l"] -= 1
        await m.answer(f"✅ +{p['r']}⭐")
    else: await m.answer("❌ Xato yoki ishlatilgan!")
    await state.clear()

# 7. STARS CHIQARISH (YECHIB OLISH)
@dp.message(F.text == "📤 Chiqarish")
async def w_draw(m: types.Message):
    btns = [(f"{g['n']} - {g['p']}⭐", f"wd_{k}") for k, g in gifts.items()]
    await m.answer("🎁 Sovg'ani tanlang:", reply_markup=ikb(btns))

@dp.callback_query(F.data.startswith("wd_"))
async def w_req(c: types.CallbackQuery):
    k = c.data.split("_")[1]
    u, g = users_db.get(c.from_user.id), gifts.get(k)
    if u["s"] < g["p"]: return await c.answer("❌ Balans yetarli emas!", show_alert=True)
    u["s"] -= g["p"]
    btns = [("✅ Tasdiq", f"ok_{c.from_user.id}_{g['p']}"), ("❌ Rad", f"no_{c.from_user.id}_{g['p']}")]
    await bot.send_message(ADMIN_ID, f"🔔 Yechish so'rovi: {c.from_user.id}\n🎁 {g['n']}", reply_markup=ikb(btns))
    await c.answer("✅ Adminga yuborildi!", show_alert=True)

@dp.callback_query(F.data.startswith("ok_"))
async def w_ok(c: types.CallbackQuery):
    uid = c.data.split("_")[1]
    await c.message.edit_text(f"{c.message.text}\n\n✅ To'landi!")
    await bot.send_message(uid, "✅ Sovg'a tasdiqlandi!")

@dp.callback_query(F.data.startswith("no_"))
async def w_no(c: types.CallbackQuery):
    _, uid, p = c.data.split("_")
    if int(uid) in users_db: users_db[int(uid)]["s"] += int(p)
    await c.message.edit_text(f"{c.message.text}\n\n❌ Rad etildi!")
    await bot.send_message(uid, f"❌ Rad etildi, sarflangan {p}⭐ qaytarildi.")

# 8. ADMIN PANEL (SODDALASHTIRILGAN QISMI)
@dp.message(F.text == "⚙️ Admin")
async def adm(m: types.Message):
    if m.from_user.id == ADMIN_ID:
        btns = [("➕ Vazifa qo'shish", "at"), ("➕ Promo qo'shish", "ap")]
        await m.answer("👨‍💻 Admin Panel", reply_markup=ikb(btns))

@dp.callback_query(F.data == "at")
async def adm_t(c: types.CallbackQuery, state: FSMContext):
    await c.message.answer("Yozing:\nFormat: `Nomi|https://t.me/kanal|@kanal_user|5`n(Orasida bo'sh joysiz tayanch chiziq bo'lsin)", parse_mode="Markdown"); await state.set_state(Adm.add_t)

@dp.message(Adm.add_t)
async def adm_t_ok(m: types.Message, state: FSMContext):
    try:
        d, u, cid, r = m.text.split("|")
        tasks_db[str(len(tasks_db)+1)] = {"d": d, "u": u, "c": cid, "r": int(r)}
        await m.answer("✅ Vazifa qo'shildi!")
    except: await m.answer("❌ Format xato!")
    await state.clear()

@dp.callback_query(F.data == "ap")
async def adm_p(c: types.CallbackQuery, state: FSMContext):
    await c.message.answer("Yozing:\nFormat: `KOD|15|100`\n(Kod | Mukofot ⭐ | Odam soni)", parse_mode="Markdown"); await state.set_state(Adm.add_p)

@dp.message(Adm.add_p)
async def adm_p_ok(m: types.Message, state: FSMContext):
    try:
        c, r, l = m.text.split("|")
        promos_db[c] = {"r": int(r), "l": int(l)}
        await m.answer("✅ Promo qo'shildi!")
    except: await m.answer("❌ Format xato!")
    await state.clear()

# 9. ISHGA TUSHIRISH
async def main():
    Thread(target=run_flask, daemon=True).start()
    await dp.start_polling(bot)

if __name__ == "__main__": asyncio.run(main())
                       
