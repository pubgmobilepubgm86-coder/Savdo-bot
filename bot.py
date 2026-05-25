import sqlite3
import logging
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, 
    CallbackQueryHandler, ContextTypes, ConversationHandler, filters
)
from flask import Flask
from threading import Thread

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = "8849139822:AAGqJL9XQck3zklSjeVRsfoQ_5vl_wtnGnQ"
MASTER_ADMIN = 8086545587
DB_NAME = 'items.db'

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS items (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, price REAL, image_id TEXT, description TEXT, category TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS cart (user_id INTEGER, item_id INTEGER, quantity INTEGER)')
    c.execute('CREATE TABLE IF NOT EXISTS admins (user_id INTEGER UNIQUE)')
    c.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)')
    c.execute('CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, status TEXT)')
    c.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (MASTER_ADMIN,))
    conn.commit()
    conn.close()

init_db()

def is_admin(user_id):
    conn = sqlite3.connect(DB_NAME)
    res = conn.execute("SELECT user_id FROM admins WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    return res is not None

def get_cart_items(user_id):
    conn = sqlite3.connect(DB_NAME)
    items = conn.execute("SELECT items.id, items.name, items.price, cart.quantity FROM cart JOIN items ON cart.item_id = items.id WHERE cart.user_id=?", (user_id,)).fetchall()
    conn.close()
    return items

ADD_CAT, ADD_NAME, ADD_PRICE, ADD_DESC, ADD_IMAGE = range(5)
ADD_ADMIN_ID, CHECKOUT_PHONE, ADMIN_REPLY_TEXT, BROADCAST_TEXT = range(5, 9)

def run_flask():
    app = Flask(__name__)
    @app.route('/')
    def home(): return "Tulpor Savdo Markazi Aktiv!"
    app.run(host='0.0.0.0', port=10000)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    conn = sqlite3.connect(DB_NAME)
    conn.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (uid,))
    conn.commit(); conn.close()
    kb = [["TOVARLAR 🌐", "🛒 Savat"], ["🚚 Yetkazib berish", "ℹ️ Biz haqimizda"]]
    if is_admin(uid): kb.append(["🛠 Admin Panel"])
    await update.message.reply_text(f"Assalomu alaykum, {update.effective_user.first_name}! Tulpor savdo markazi botiga xush kelibsiz.", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))

async def handle_main_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text, uid = update.message.text, update.effective_user.id
    if text == "TOVARLAR 🌐":
        conn = sqlite3.connect(DB_NAME); cats = conn.execute("SELECT DISTINCT category FROM items").fetchall(); conn.close()
        if not cats: await update.message.reply_text("Hozircha tovar yo'q.")
        else:
            kb = [[InlineKeyboardButton(c[0], callback_data=f"cat_{c[0]}")] for c in cats if c[0]]
            await update.message.reply_text("Kerakli guruhni tanlang:", reply_markup=InlineKeyboardMarkup(kb))
    elif text == "🛒 Savat":
        cart = get_cart_items(uid)
        if not cart: await update.message.reply_text("Savat bo'sh.")
        else:
            msg = "🛒 Savat tarkibi:\n\n"; total = 0
            for i_id, name, price, qty in cart:
                total += price * qty
                msg += f"🔹 {name} - {qty} ta x {price:,.0f} = {price*qty:,.0f} so'm\n"
            msg += f"\n💵 Jami summa: {total:,.0f} so'm"
            kb = [[InlineKeyboardButton("🚖 Buyurtma berish", callback_data="checkout_start")], [InlineKeyboardButton("🗑 Savatni tozalash", callback_data="clear_cart")]]
            await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(kb))
    elif text == "🛠 Admin Panel" and is_admin(uid):
        conn = sqlite3.connect(DB_NAME)
        users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        pending = conn.execute("SELECT COUNT(*) FROM orders WHERE status='Kutilmoqda'").fetchone()[0]
        done = conn.execute("SELECT COUNT(*) FROM orders WHERE status='Yetkazildi'").fetchone()[0]
        conn.close()
        msg = (f"📊 TULPOR SAVDO MARKAZI STATISTIKASI\n\n"
               f"👤 Foydalanuvchilar: {users} ta\n"
               f"⏳ Yetkazilishi kerak: {pending} ta\n"
               f"✅ Yetkazilganlar: {done} ta")
        kb = [[InlineKeyboardButton("➕ Tovar qo'shish", callback_data='add_item'), InlineKeyboardButton("❌ Tovar o'chirish", callback_data='del_item')],
              [InlineKeyboardButton("👤 Admin qo'shish", callback_data='add_admin'), InlineKeyboardButton("📢 Barchaga xabar", callback_data='broadcast_start')]]
        await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(kb))

async def button_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    data, uid = query.data, query.from_user.id
    if data.startswith("cat_"):
        cat = data.replace("cat_", "")
        conn = sqlite3.connect(DB_NAME); items = conn.execute("SELECT id, name FROM items WHERE category=?", (cat,)).fetchall(); conn.close()
        kb = [[InlineKeyboardButton(i[1], callback_data=f"show_{i[0]}")] for i in items]
        await query.message.edit_text(f"📦 {cat} guruhidagi tovarlar:", reply_markup=InlineKeyboardMarkup(kb))
    elif data.startswith("show_"):
        item_id = int(data.replace("show_", ""))
        conn = sqlite3.connect(DB_NAME); item = conn.execute("SELECT name, price, image_id, description FROM items WHERE id=?", (item_id,)).fetchone(); conn.close()
        if item:
            kb = [[InlineKeyboardButton("📥 Savatga qo'shish", callback_data=f"add_to_cart_{item_id}")]]
            await query.message.reply_photo(photo=item[2], caption=f"📌 Nomi: {item[0]}\n💰 Narxi: {item[1]:,.0f} so'm\n📝 Info: {item[3]}", reply_markup=InlineKeyboardMarkup(kb))
    elif data.startswith("add_to_cart_"):
        item_id = int(data.replace("add_to_cart_", ""))
        conn = sqlite3.connect(DB_NAME); exist = conn.execute("SELECT quantity FROM cart WHERE user_id=? AND item_id=?", (uid, item_id)).fetchone()
        if exist: conn.execute("UPDATE cart SET quantity = quantity + 1 WHERE user_id=? AND item_id=?", (uid, item_id))
        else: conn.execute("INSERT INTO cart (user_id, item_id, quantity) VALUES (?, ?, 1)", (uid, item_id))
        conn.commit(); conn.close()
        await query.message.reply_text("✅ Mahsulot savatga qo'shildi!")
    elif data == "clear_cart":
        conn = sqlite3.connect(DB_NAME); conn.execute("DELETE FROM cart WHERE user_id=?", (uid,)); conn.commit(); conn.close()
        await query.message.edit_text("🗑 Savatingiz tozalandi!")
    elif data.startswith("done_") and is_admin(uid):
        order_id = int(data.split("_")[1])
        conn = sqlite3.connect(DB_NAME); conn.execute("UPDATE orders SET status='Yetkazildi' WHERE id=?", (order_id,)); conn.commit(); conn.close()
        await query.message.edit_text("✅ Buyurtma holati 'Yetkazildi' deb belgilandi!")
    elif data == "del_item" and is_admin(uid):
        conn = sqlite3.connect(DB_NAME); items = conn.execute("SELECT id, name FROM items").fetchall(); conn.close()
        kb = [[InlineKeyboardButton(f"❌ {i[1]}", callback_data=f"del_{i[0]}")] for i in items]
        await query.message.reply_text("O'chirish uchun tovarni tanlang:", reply_markup=InlineKeyboardMarkup(kb))
    elif data.startswith("del_") and is_admin(uid):
        conn = sqlite3.connect(DB_NAME); conn.execute("DELETE FROM items WHERE id=?", (int(data.replace("del_", "")),)); conn.commit(); conn.close()
        await query.message.edit_text("✅ Tovar o'chirildi.")

async def add_item_start(update, context): await update.callback_query.message.reply_text("Kategoriyani yozing:"); return ADD_CAT
async def get_item_cat(update, context): context.user_data['cat'] = update.message.text; await update.message.reply_text("Nomini:"); return ADD_NAME
async def get_item_name(update, context): context.user_data['name'] = update.message.text; await update.message.reply_text("Narxini:"); return ADD_PRICE
async def get_item_price(update, context):
    try: context.user_data['price'] = float(update.message.text.replace(" ", "")); await update.message.reply_text("Tavsif:"); return ADD_DESC
    except: await update.message.reply_text("Faqat raqam:"); return ADD_PRICE
async def get_item_desc(update, context): context.user_data['desc'] = update.message.text; await update.message.reply_text("Rasm:"); return ADD_IMAGE
async def get_item_image(update, context):
    conn = sqlite3.connect(DB_NAME); conn.execute("INSERT INTO items (name, price, image_id, description, category) VALUES (?, ?, ?, ?, ?)", (context.user_data['name'], context.user_data['price'], update.message.photo[-1].file_id, context.user_data['desc'], context.user_data['cat'])); conn.commit(); conn.close()
    await update.message.reply_text("✅ Tovar qo'shildi!"); return ConversationHandler.END

async def add_admin_start(update, context): await update.callback_query.message.reply_text("Yangi admin ID:"); return ADD_ADMIN_ID
async def get_new_admin_id(update, context):
    conn = sqlite3.connect(DB_NAME); conn.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (int(update.message.text),)); conn.commit(); conn.close()
    await update.message.reply_text("✅ Admin qo'shildi!"); return ConversationHandler.END

async def checkout_start(update, context): await update.callback_query.message.reply_text("📞 Telefon:"); return CHECKOUT_PHONE
async def get_checkout_phone(update, context):
    user = update.effective_user; cart = get_cart_items(user.id)
    conn = sqlite3.connect(DB_NAME); cursor = conn.cursor(); cursor.execute("INSERT INTO orders (user_id, status) VALUES (?, 'Kutilmoqda')", (user.id,))
    order_id = cursor.lastrowid; conn.commit(); conn.close()
    msg = f"🔔 YANGI BUYURTMA #{order_id}!\nMijoz: {user.full_name}\nTel: {update.message.text}"
    kb = [[InlineKeyboardButton("📩 Javob", callback_data=f"reply_{user.id}"), InlineKeyboardButton("✅ Yetkazildi", callback_data=f"done_{order_id}")]]
    conn = sqlite3.connect(DB_NAME); adms = conn.execute("SELECT user_id FROM admins").fetchall(); conn.close()
    for adm in adms: 
        try: await context.bot.send_message(chat_id=adm[0], text=msg, reply_markup=InlineKeyboardMarkup(kb))
        except: pass
    conn = sqlite3.connect(DB_NAME); conn.execute("DELETE FROM cart WHERE user_id=?", (user.id,)); conn.commit(); conn.close()
    await update.message.reply_text("✅ Qabul qilindi!"); return ConversationHandler.END

async def admin_reply_start(update, context): context.user_data['reply_target_id'] = int(update.callback_query.data.split("_")[1]); await update.callback_query.message.reply_text("Javob:"); return ADMIN_REPLY_TEXT
async def admin_send_reply(update, context): await context.bot.send_message(chat_id=context.user_data['reply_target_id'], text=f"✉️ Admin: {update.message.text}"); await update.message.reply_text("✅ Yetkazildi!"); return ConversationHandler.END

async def broadcast_start(update, context): await update.callback_query.message.reply_text("📢 Xabar:"); return BROADCAST_TEXT
async def send_broadcast(update, context):
    conn = sqlite3.connect(DB_NAME); users = conn.execute("SELECT user_id FROM users").fetchall(); conn.close()
    for u in users:
        try: await context.bot.send_message(chat_id=u[0], text=update.message.text)
        except: pass
    await update.message.reply_text("✅ Yuborildi!"); return ConversationHandler.END

async def cancel(update, context): await update.message.reply_text("Bekor qilindi."); return ConversationHandler.END

def main():
    Thread(target=run_flask, daemon=True).start()
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(ConversationHandler(entry_points=[CallbackQueryHandler(add_item_start, pattern='^add_item$')], states={ADD_CAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_item_cat)], ADD_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_item_name)], ADD_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_item_price)], ADD_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_item_desc)], ADD_IMAGE: [MessageHandler(filters.PHOTO, get_item_image)]}, fallbacks=[CommandHandler('cancel', cancel)]))
    app.add_handler(ConversationHandler(entry_points=[CallbackQueryHandler(add_admin_start, pattern='^add_admin$')], states={ADD_ADMIN_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_new_admin_id)]}, fallbacks=[CommandHandler('cancel', cancel)]))
    app.add_handler(ConversationHandler(entry_points=[CallbackQueryHandler(checkout_start, pattern='^checkout_start$')], states={CHECKOUT_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_checkout_phone)]}, fallbacks=[CommandHandler('cancel', cancel)]))
    app.add_handler(ConversationHandler(entry_points=[CallbackQueryHandler(admin_reply_start, pattern='^reply_\\d+$')], states={ADMIN_REPLY_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_send_reply)]}, fallbacks=[CommandHandler('cancel', cancel)]))
    app.add_handler(ConversationHandler(entry_points=[CallbackQueryHandler(broadcast_start, pattern='^broadcast_start$')], states={BROADCAST_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, send_broadcast)]}, fallbacks=[CommandHandler('cancel', cancel)]))
    app.add_handler(CallbackQueryHandler(button_router))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_main_text))
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__': main()
            
