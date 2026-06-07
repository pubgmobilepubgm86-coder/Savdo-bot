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
settings_db = {"ref_reward": 5} # Referal uchun standart mukofot
gifts_db = {"1": {"name": "🧸 Ayiqcha", "price": 15}, "2": {"name": "💎 TG Premium (1 oy)", "price": 250}}

# ---- SERVER ----
@app.route('/')
def home(): return "Stars Mines Free boti 24/7 ishlamoqda!"

# ---- FSM HOLATLARI ----
class AdminState(StatesGroup):
    t_photo, t_url, t_chat_id, t_reward = State(), State(), State(), State()
    g_name, g_price = State(), State()
    p_code, p_reward, p_limit = State(), State(), State()
    a_id, a_amount = State(), State()
    ref_reward = State()
class UserPromo(StatesGroup): code = State()

# ---- KLAVIATURALAR ----
def main_menu(uid):
    btns = [
        "💎 Stars ishlash (O'yinlar)", "📋 Vazifalar (Free Stars)", 
        "👥 Do'stlarni taklif qilish", "🎟 Promokod",
        "👤 Profil", "📤 Stars chiqarish", 
        "🏆 Top Konchilar", "ℹ️ Malumot / Qoidalar"
    ]
    if uid == ADMIN_ID: btns.append("⚙️ Admin Panel")
    b = ReplyKeyboardBuilder()
    [b.add(types.KeyboardButton(text=t)) for t in btns]
    return b.adjust(2, 2, 2, 2, 1).as_markup(resize_keyboard=True)

def inline_btn(btn_data, adjust_val=1):
    b = InlineKeyboardBuilder()
    [b.button(text=text, **( {"url": cb} if str(cb).startswith("http") else {"callback_data": cb} )) for text, cb in btn_data]
    return b.adjust(adjust_val).as_markup()

# ---- START VA REFERAL ----
@dp.message(CommandStart())
async def start(m: types.Message):
    uid = m.from_user.id
    args = m.text.split()
    
    if uid not in users_db:
        users_db[uid] = {"name": m.from_user.first_name, "stars": 0, "attempts": 10, "tasks": [], "promos": []}
        
        # Referal tekshirish
        if len(args) > 1 and args[1].isdigit():
            ref_id = int(args[1])
            if ref_id in users_db and ref_id != uid:
                reward = settings_db["ref_reward"]
                users_db[ref_id]["stars"] += reward
                await bot.send_message(ref_id, f"🎉 **Tabriklaymiz!** Sizning taklif havolangiz orqali do'stingiz botga qo'shildi.\n💎 Sizga **{reward} ⭐** berildi!", parse_mode="Markdown")

    await m.answer(f"👋 **Salom, {m.from_user.first_name}!**\n🌟 **Stars Mines Free** platformasiga xush kelibsiz!", parse_mode="Markdown", reply_markup=main_menu(uid))

# ---- REFERAL MENU ----
@dp.message(F.text == "👥 Do'stlarni taklif qilish")
async def ref_menu(m: types.Message):
    bot_info = await bot.get_me()
    link = f"https://t.me/{bot_info.username}?start={m.from_user.id}"
    await m.answer(f"👥 **Referal Dasturi**\n\nSizning shaxsiy taklif havolangiz:\n👉 `{link}`\n\nHar bir taklif qilingan do'stingiz uchun **{settings_db['ref_reward']} ⭐** olasiz!", parse_mode="Markdown")

# ---- PROFIL, QOIDALAR, TOP ----
@dp.message(F.text == "👤 Profil")
async def profile(m: types.Message):
    u = users_db.get(m.from_user.id, {"stars": 0, "attempts": 0})
    await m.answer(f"👤 **Profil:**\n🆔 `{m.from_user.id}`\n💎 Balans: **{u['stars']} ⭐**\n⚡ Energiya: **{u['attempts']}** marta", parse_mode="Markdown")

@dp.message(F.text == "ℹ️ Malumot / Qoidalar")
async def rules(m: types.Message):
    await m.answer("ℹ️ Botda vazifa, oʻyin va promokod orqali Stars ishlaysiz (Min. 15⭐).\n⚠️ **Qoidalar:** Nakrutka qat'iyan man etiladi, hisob bloklanadi!", parse_mode="Markdown")

@dp.message(F.text == "🏆 Top Konchilar")
async def leaders(m: types.Message):
    t = "🏆 **Top-5 Konchilar:**\n\n" + "".join([f"{i}. {d['name']} — {d['stars']} ⭐\n" for i, (k, d) in enumerate(sorted(users_db.items(), key=lambda x: x[1]['stars'], reverse=True)[:5], 1)]) if users_db else "Hali ro'yxat bo'sh!"
    await m.answer(t, parse_mode="Markdown")

# ---- VAZIFALAR VA HAQIQIY TEKSHIRUV ----
@dp.message(F.text == "📋 Vazifalar (Free Stars)")
async def tasks(m: types.Message):
    avail = [t for t in tasks_db if t not in users_db.get(m.from_user.id, {}).get("tasks", [])]
    if not avail: return await m.answer("🎉 Hozircha barcha vazifalarni bajarib bo'ldingiz!")
    for t_id in avail:
        t = tasks_db[t_id]
        cap = f"📝 **Vazifa:** {t['desc']}\n💎 **Mukofot:** {t['reward']} ⭐"
        rm = inline_btn([("🔗 Kanalga kirish", t['url']), ("✅ Tasdiqlash", f"chk_t_{t_id}")])
        if t.get('photo') != "none": await m.answer_photo(t['photo'], caption=cap, parse_mode="Markdown", reply_markup=rm)
        else: await m.answer(cap, parse_mode="Markdown", reply_markup=rm)

@dp.callback_query(F.data.startswith("chk_t_"))
async def chk_task(c: types.CallbackQuery):
    tid = c.data.split("_")[2]
    uid = c.from_user.id
    u = users_db.get(uid)
    t = tasks_db.get(tid)
    
    if not t: return await c.answer("❌ Bu vazifa mavjud emas!", show_alert=True)
    if tid in u.get("tasks", []): return await c.answer("✅ Siz bu vazifani avval bajargansiz!", show_alert=True)
    
    # OBUNANI TEKSHIRISH
    try:
        member = await bot.get_chat_member(chat_id=t['chat_id'], user_id=uid)
        if member.status not in ['member', 'administrator', 'creator']:
            return await c.answer("❌ Siz hali kanalga/guruhga a'zo bo'lmagansiz!", show_alert=True)
    except Exception as e:
        return await c.answer("❌ Xatolik: Bot ushbu kanalga admin qilinmagan yoki ID xato!", show_alert=True)
        
    # Agar a'zo bo'lsa mukofot beriladi
    r = t['reward']
    u["stars"] += r
    u.setdefault("tasks", []).append(tid)
    try: await c.message.delete()
    except: pass
    await c.answer(f"✅ Tasdiqlandi! +{r} Stars!", show_alert=True)
    await bot.send_message(uid, f"💎 Vazifa muvaffaqiyatli tekshirildi! Balansingizga {r} Stars qo'shildi.")

# ---- PROMOKOD ----
@dp.message(F.text == "🎟 Promokod")
async def pr_st(m: types.Message, state: FSMContext): await m.answer("🎟 Promokodni kiriting:"), await state.set_state(UserPromo.code)
@dp.message(UserPromo.code)
async def pr_ap(m: types.Message, state: FSMContext):
    c, u = m.text.strip(), users_db.get(m.from_user.id)
    if c in promocodes_db and promocodes_db[c]["limit"] > 0 and c not in u.get("promos", []):
        u["stars"] += promocodes_db[c]["reward"]; u.setdefault("promos", []).append(c); promocodes_db[c]["limit"] -= 1
        await m.answer(f"✅ Qabul qilindi! +{promocodes_db[c]['reward']} ⭐")
    else: await m.answer("❌ Xato kiritdingiz, ishlatilgan yoki limit tugagan.")
    await state.clear()

# ---- O'YINLAR ----
@dp.message(F.text == "💎 Stars ishlash (O'yinlar)")
async def p_game(m: types.Message): await m.answer("🎮 Menga stikerlardan birini yuboring:\n🎯 (Darts), 🎲 (Kubik) yoki 🏀 (Basketbol)")
@dp.message(F.dice)
async def dice(m: types.Message):
    if m.dice.emoji not in ["🎯", "🎲", "🏀"] or m.from_user.id not in users_db: return
    u = users_db[m.from_user.id]
    if u["attempts"] <= 0: return await m.answer("😔 Bugungi o'yin energiyasi tugadi.")
    u["attempts"] -= 1; await asyncio.sleep(2.5)
    win = (m.dice.value == 6 and m.dice.emoji in ["🎯", "🎲"]) or (m.dice.emoji == "🏀" and m.dice.value in [4, 5])
    if win: u["stars"] += 1
    await m.answer(f"🎉 **YUTUQ!** +1 ⭐\n⚡ Energiya: {u['attempts']}" if win else f"❌ Nishonga tegmadi.\n⚡ Energiya: {u['attempts']}", parse_mode="Markdown")

# ---- CHIQARISH VA ADMIN TASDIQLASHI ----
@dp.message(F.text == "📤 Stars chiqarish")
async def w_draw(m: types.Message):
    rm = inline_btn([(f"{g['name']} - {g['price']} ⭐", f"buy_{gid}") for gid, g in gifts_db.items()])
    await m.answer(f"📤 Sizning balansingiz: **{users_db.get(m.from_user.id, {}).get('stars', 0)} ⭐**\n(Minimal miqdor: 15 ⭐)\n\n🎁 Quyidagi sovg'alardan birini tanlang:", parse_mode="Markdown", reply_markup=rm)

@dp.callback_query(F.data.startswith("buy_"))
async def w_buy(c: types.CallbackQuery):
    gid, uid, u = c.data.split("_")[1], c.from_user.id, users_db.get(c.from_user.id)
    if gid in gifts_db:
        g = gifts_db[gid]
        if u["stars"] < 15 or u["stars"] < g["price"]: return await c.answer("❌ Balans yetarli emas!", show_alert=True)
        u["stars"] -= g["price"]
        
        # Adminga tugmalar bilan yuborish
        kb = InlineKeyboardBuilder()
        kb.button(text="✅ Tasdiqlash", callback_data=f"wok_{uid}_{g['price']}")
        kb.button(text="❌ Rad etish", callback_data=f"wno_{uid}_{g['price']}")
        admin_msg = f"🔔 <b>YANGI SOVG'A SO'ROVI!</b>\n\n👤 Ism: {c.from_user.full_name}\n🆔 ID: <code>{uid}</code>\n🎁 Tanladi: {g['name']}\n💎 To'ladi: {g['price']} ⭐"
        await bot.send_message(ADMIN_ID, admin_msg, parse_mode="HTML", reply_markup=kb.as_markup())
        await c.answer("✅ So'rovingiz adminga yuborildi. Kuting!", show_alert=True)

# Admin Tasdiqlash/Rad etish
@dp.callback_query(F.data.startswith("wok_"))
async def w_ok(c: types.CallbackQuery):
    _, uid, price = c.data.split("_")
    new_text = c.message.html_text + f"\n\n✅ <b>TASDIQLANDI VA YUBORILDI!</b>\n🔗 <a href='tg://user?id={uid}'>Foydalanuvchi profiliga o'tish</a>"
    await c.message.edit_text(new_text, parse_mode="HTML")
    await bot.send_message(int(uid), "✅ <b>Tabriklaymiz!</b> Sizning sovg'a so'rovingiz admin tomonidan tasdiqlandi va amalga oshirildi!", parse_mode="HTML")

@dp.callback_query(F.data.startswith("wno_"))
async def w_no(c: types.CallbackQuery):
    _, uid, price = c.data.split("_")
    uid, price = int(uid), int(price)
    if uid in users_db: users_db[uid]["stars"] += price # Puli qaytariladi
    new_text = c.message.html_text + "\n\n❌ <b>RAD ETILDI</b> (Stars qaytarildi)"
    await c.message.edit_text(new_text, parse_mode="HTML")
    await bot.send_message(uid, f"❌ <b>Rad etildi!</b>\nSizning sovg'a so'rovingiz bekor qilindi. {price} ⭐ hisobingizga qaytarildi.", parse_mode="HTML")

# ================= ADMIN PANEL =================
@dp.message(F.text == "⚙️ Admin Panel")
async def adm_p(m: types.Message):
    if m.from_user.id != ADMIN_ID: return
    btns = [
        ("➕ Vazifa", "a_t_add"), ("➖ Vazifa", "a_t_del"), 
        ("🎁 Sovg'a", "a_g_add"), ("🗑 Sovg'a", "a_g_del"), 
        ("🎟 Promo", "a_p_add"), ("🔗 Ref Narxi", "a_ref"),
        ("💰 Hisob", "a_acc"), ("📊 Stat", "a_stat")
    ]
    await m.answer("👨‍💻 **Admin Panel**\nO'zgarishlar qiling:", parse_mode="Markdown", reply_markup=inline_btn(btns, 2))

@dp.callback_query(F.data == "a_stat")
async def a_stat(c: types.CallbackQuery): await c.answer(f"📊 Jami a'zolar: {len(users_db)} ta", show_alert=True)

# Admin: Referal narxini sozlash
@dp.callback_query(F.data == "a_ref")
async def a_ref1(c: types.CallbackQuery, state: FSMContext):
    await c.message.answer(f"Hozirgi taklif narxi: {settings_db['ref_reward']} ⭐\nYangi narxni yozing (faqat raqam):")
    await state.set_state(AdminState.ref_reward)
@dp.message(AdminState.ref_reward)
async def a_ref2(m: types.Message, state: FSMContext):
    if m.text.isdigit():
        settings_db["ref_reward"] = int(m.text)
        await m.answer(f"✅ Yangi referal narxi o'rnatildi: {m.text} ⭐")
    else: await m.answer("❌ Faqat raqam yozing.")
    await state.clear()

# Admin: Vazifa qo'shish (Tekshiruv uchun ID bilan)
@dp.callback_query(F.data == "a_t_add")
async def t_a1(c: types.CallbackQuery, state: FSMContext): await c.message.answer("1️⃣ Rasm yuboring (yoki 'yoq' yozing) tagiga matn yozing:"), await state.set_state(AdminState.t_photo)
@dp.message(AdminState.t_photo)
async def t_a2(m: types.Message, state: FSMContext): await state.update_data(p=m.photo[-1].file_id if m.photo else "none", d=m.caption or m.text), await m.answer("2️⃣ Foydalanuvchi bosishi uchun **Havola (URL)** yuboring (Masalan: https://t.me/kanalim):"), await state.set_state(AdminState.t_url)
@dp.message(AdminState.t_url)
async def t_a3(m: types.Message, state: FSMContext): await state.update_data(u=m.text), await m.answer("3️⃣ Bot obunani tekshirishi uchun kanal **Usernameni yoki ID** sini bering.\n(Masalan: `@kanalim` yoki `-100123456789`) \n⚠️ *Eslatma:* Bot shu kanalga admin qilinishi shart!"), await state.set_state(AdminState.t_chat_id)
@dp.message(AdminState.t_chat_id)
async def t_a4(m: types.Message, state: FSMContext): await state.update_data(c_id=m.text), await m.answer("4️⃣ Vazifa mukofoti necha Stars?"), await state.set_state(AdminState.t_reward)
@dp.message(AdminState.t_reward)
async def t_a5(m: types.Message, state: FSMContext): 
    if not m.text.isdigit(): return await m.answer("Faqat raqam kiriting!")
    d = await state.get_data()
    tasks_db[str(len(tasks_db)+1)] = {"photo": d['p'], "desc": d['d'], "url": d['u'], "chat_id": d['c_id'], "reward": int(m.text)}
    await m.answer("✅ Mukammal, vazifa muvaffaqiyatli qo'shildi!"); await state.clear()

@dp.callback_query(F.data == "a_t_del")
async def t_d1(c: types.CallbackQuery): await c.message.answer("🗑 Qaysi vazifani o'chiramiz?", reply_markup=inline_btn([(f"🗑 {t['desc']}", f"d_t_{tid}") for tid, t in tasks_db.items()]))
@dp.callback_query(F.data.startswith("d_t_"))
async def t_d2(c: types.CallbackQuery): tasks_db.pop(c.data.split("_")[2], None); await c.message.edit_text("✅ O'chirildi!")

# Admin: Sovg'a qo'shish va o'chirish
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

# Admin: Promokod
@dp.callback_query(F.data == "a_p_add")
async def p_a1(c: types.CallbackQuery, state: FSMContext): await c.message.answer("🎟 Kod matni:"), await state.set_state(AdminState.p_code)
@dp.message(AdminState.p_code)
async def p_a2(m: types.Message, state: FSMContext): await state.update_data(c=m.text.strip()), await m.answer("💎 Mukofot (⭐):"), await state.set_state(AdminState.p_reward)
@dp.message(AdminState.p_reward)
async def p_a3(m: types.Message, state: FSMContext): await state.update_data(r=int(m.text)), await m.answer("👥 Limit necha marta?"), await state.set_state(AdminState.p_limit)
@dp.message(AdminState.p_limit)
async def p_a4(m: types.Message, state: FSMContext):
    d = await state.get_data(); promocodes_db[d['c']] = {"reward": d['r'], "limit": int(m.text)}
    await m.answer(f"✅ Promo yaratildi: `{d['c']}`", parse_mode="Markdown"); await state.clear()

# Admin: Hisob menejeri
@dp.callback_query(F.data == "a_acc")
async def ac_1(c: types.CallbackQuery, state: FSMContext): await c.message.answer("👤 Foydalanuvchi IDsi:"), await state.set_state(AdminState.a_id)
@dp.message(AdminState.a_id)
async def ac_2(m: types.Message, state: FSMContext):
    if not m.text.isdigit() or int(m.text) not in users_db: return await m.answer("❌ ID xato yoki topilmadi."), await state.clear()
    await state.update_data(id=int(m.text)), await m.answer(f"Balans: {users_db[int(m.text)]['stars']}⭐\nQo'shish/Ayirish (masalan: 50 yoki -20):"), await state.set_state(AdminState.a_amount)
@dp.message(AdminState.a_amount)
async def ac_3(m: types.Message, state: FSMContext):
    uid = (await state.get_data())['id']; users_db[uid]['stars'] = max(0, users_db[uid]['stars'] + int(m.text))
    await m.answer(f"✅ Bajarildi! Yangi balans: {users_db[uid]['stars']} ⭐")
    await bot.send_message(uid, f"🔔 Admin hisobingizni o'zgartirdi.\nYangi balansingiz: **{users_db[uid]['stars']} ⭐**", parse_mode="Markdown"); await state.clear()

# ---- ISHGA TUSHIRISH ----
async def main():
    Thread(target=lambda: app.run(host="0.0.0.0", port=PORT), daemon=True).start()
    await dp.start_polling(bot)

if __name__ == "__main__": asyncio.run(main())
                
