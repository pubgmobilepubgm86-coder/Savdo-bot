import sqlite3
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import (ApplicationBuilder, CommandHandler, MessageHandler, 
                          CallbackQueryHandler, ContextTypes, ConversationHandler, filters)
from flask import Flask
from threading import Thread

# Loglarni sozlash
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

TOKEN = "8849139822:AAEOia8xieoZ9kfUZjKadw7z6JcQ0cSZ1oY"
MASTER_ADMIN = 8086545587

# --- BAZA VA FUNKSIYALAR ---
def init_db():
    conn = sqlite3.connect('items.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS items (name TEXT, price TEXT, image_id TEXT, description TEXT, category TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS cart (user_id INTEGER, item_id INTEGER, quantity TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS admins (user_id INTEGER)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)''')
    if not cursor.execute("SELECT * FROM admins WHERE user_id=?", (MASTER_ADMIN,)).fetchone():
        cursor.execute("INSERT INTO admins VALUES (?)", (MASTER_ADMIN,))
    conn.commit()
    conn.close()

init_db()

CATEGORY, NAME, PRICE, DESC, IMAGE, QUANTITY, PHONE, NEW_ADMIN, REPLY = range(9)

def run_flask():
    app_flask = Flask(__name__)
    @app_flask.route('/')
    def home(): return "Bot ishlayapti!"
    app_flask.run(host='0.0.0.0', port=10000)

def is_admin(user_id):
    conn = sqlite3.connect('items.db')
    res = conn.execute("SELECT * FROM admins WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    return res is not None

# --- ASOSIY MENYU ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conn = sqlite3.connect('items.db')
    conn.execute("INSERT OR IGNORE INTO users VALUES (?)", (user_id,))
    conn.commit()
    conn.close()
    
    kb = [["TOVARLAR 🌐", "🛒 Savat"], ["🚚 Yetkazib berish", "ℹ️ Biz haqimizda"]]
    if is_admin(user_id): kb.append(["🛠 Admin Panel"])
    await update.message.reply_text("Assalomu alaykum! Tulpor yemlari botiga xush kelibsiz.", 
                                    reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))

async def handle_main(update, context):
    text = update.message.text
    if text == "TOVARLAR 🌐":
        conn = sqlite3.connect('items.db')
        cats = conn.execute("SELECT DISTINCT category FROM items").fetchall()
        conn.close()
        if not cats: await update.message.reply_text("Hozircha tovarlar yo'q.")
        else:
            kb = [[InlineKeyboardButton(c[0], callback_data=f"cat_{c[0]}")] for c in cats]
            await update.message.reply_text("Guruhni tanlang:", reply_markup=InlineKeyboardMarkup(kb))
    elif text == "🛒 Savat": await show_cart(update, context)
    elif text == "🚚 Yetkazib berish": await update.message.reply_text("🚚 Chortoq bo'ylab yetkazib berish xizmatimiz mavjud.")
    elif text == "ℹ️ Biz haqimizda": await update.message.reply_text("Tulpor yemlari - sifatli mahsulotlar!")
    elif text == "🛠 Admin Panel" and is_admin(update.effective_user.id):
        kb = [[InlineKeyboardButton("➕ Tovar qo'shish", callback_data='add_item'), InlineKeyboardButton("➖ Tovar o'chirish", callback_data='del_item')],
              [InlineKeyboardButton("📊 Statistika", callback_data='show_stats')]]
        if update.effective_user.id == MASTER_ADMIN:
            kb.append([InlineKeyboardButton("👤 Yangi admin qo'shish", callback_data='add_admin')])
        await update.message.reply_text("Admin boshqaruvi:", reply_markup=InlineKeyboardMarkup(kb))

# --- TOVARLAR BILAN ISHLASH ---
async def add_start(update, context):
    query = update.callback_query
    await query.answer()
    conn = sqlite3.connect('items.db')
    cats = conn.execute("SELECT DISTINCT category FROM items").fetchall()
    conn.close()
    kb = [[InlineKeyboardButton(c[0], callback_data=f"selcat_{c[0]}")] for c in cats]
    kb.append([InlineKeyboardButton("➕ Yangi guruh", callback_data="new_cat")])
    await query.message.edit_text("Guruhni tanlang:", reply_markup=InlineKeyboardMarkup(kb))
    return CATEGORY

async def select_cat(update, context):
    query = update.callback_query
    await query.answer()
    if query.data == "new_cat":
        await query.message.edit_text("Yangi guruh nomini yozing:")
        return CATEGORY
    context.user_data['cat'] = query.data.split("_")[1]
    await query.message.edit_text(f"Tanlandi: {context.user_data['cat']}. Tovar nomini yozing:")
    return NAME

async def get_cat_name(update, context):
    context.user_data['cat'] = update.message.text
    await update.message.reply_text("Tovar nomini yozing:")
    return NAME

async def get_name(update, context):
    context.user_data['name'] = update.message.text
    await update.message.reply_text("Narxini yozing:")
    return PRICE

async def get_price(update, context):
    context.user_data['price'] = update.message.text
    await update.message.reply_text("Tavsifini yozing:")
    return DESC

async def get_desc(update, context):
    context.user_data['desc'] = update.message.text
    await update.message.reply_text("Rasmni yuboring:")
    return IMAGE

async def get_image(update, context):
    conn = sqlite3.connect('items.db')
    conn.execute("INSERT INTO items VALUES (?, ?, ?, ?, ?)", (context.user_data['name'], context.user_data['price'], update.message.photo[-1].file_id, context.user_data['desc'], context.user_data['cat']))
    conn.commit()
    conn.close()
    await update.message.reply_text("✅ Tovar qo'shildi!")
    return ConversationHandler.END

async def del_item_menu(update, context):
    query = update.callback_query
    conn = sqlite3.connect('items.db')
    items = conn.execute("SELECT rowid, name FROM items").fetchall()
    conn.close()
    kb = [[InlineKeyboardButton(f"❌ {i[1]}", callback_data=f"del_{i[0]}")] for i in items]
    await query.message.reply_text("O'chirish uchun tovarni tanlang:", reply_markup=InlineKeyboardMarkup(kb))

async def perform_delete(update, context):
    query = update.callback_query
    item_id = query.data.split("_")[1]
    conn = sqlite3.connect('items.db')
    conn.execute("DELETE FROM items WHERE rowid = ?", (item_id,))
    conn.commit()
    conn.close()
    await query.answer("O'chirildi!")
    await query.message.edit_text("✅ Tovar o'chirildi.")

# --- STATISTIKA ---
async def show_stats(update, context):
    conn = sqlite3.connect('items.db')
    count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    users = conn.execute("SELECT user_id FROM users").fetchall()
    conn.close()
    user_list = "\n".join([str(u[0]) for u in users])
    await update.callback_query.message.reply_text(f"📊 **Bot foydalanuvchilari soni:** {count}\n\nIDlar:\n{user_list}")

# --- SAVAT, BUYURTMA, JAVOB ---
async def show_cart(update, context):
    conn = sqlite3.connect('items.db')
    cart = conn.execute("SELECT i.name, c.quantity FROM cart c JOIN items i ON c.item_id = i.rowid WHERE c.user_id = ?", (update.effective_user.id,)).fetchall()
    conn.close()
    if not cart: await update.message.reply_text("🛒 Savatingiz bo'sh.")
    else:
        text = "🛒 *Sizning savatingiz:*\n" + "\n".join([f"• {i[0]} — {i[1]}" for i in cart])
        kb = [[InlineKeyboardButton("✅ Rasmiylashtirish", callback_data="checkout")]]
        await update.message.reply_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(kb))

async def checkout_start(update, context):
    await update.callback_query.message.reply_text("📞 Telefon raqamingizni qoldiring:")
    return PHONE

async def get_phone(update, context):
    phone = update.message.text
    user = update.effective_user
    conn = sqlite3.connect('items.db')
    cart = conn.execute("SELECT i.name, c.quantity FROM cart c JOIN items i ON c.item_id = i.rowid WHERE c.user_id = ?", (user.id,)).fetchall()
    admins = conn.execute("SELECT user_id FROM admins").fetchall()
    conn.close()
    order_details = "\n".join([f"• {i[0]} — {i[1]}" for i in cart])
    msg = f"🆕 *Yangi buyurtma!*\n👤 Mijoz: {user.full_name}\n📞 Raqam: {phone}\n📦 Tovar:\n{order_details}"
    for admin in admins:
        kb = [[InlineKeyboardButton("📩 Javob berish", callback_data=f"reply_{user.id}")]]
        await context.bot.send_message(chat_id=admin[0], text=msg, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(kb))
    await update.message.reply_text("✅ Buyurtmangiz qabul qilindi!")
    return ConversationHandler.END

async def reply_start(update, context):
    query = update.callback_query
    context.user_data['target_user'] = query.data.split("_")[1]
    await query.message.reply_text("Mijozga yuboriladigan javobni yozing:")
    return REPLY

async def send_reply(update, context):
    await context.bot.send_message(chat_id=context.user_data['target_user'], text=f"Admin javobi: {update.message.text}")
    await update.message.reply_text("✅ Javob yuborildi!")
    return ConversationHandler.END

async def add_admin_start(update, context):
    await update.callback_query.message.reply_text("Yangi adminning ID raqamini kiriting:")
    return NEW_ADMIN

async def save_admin(update, context):
    conn = sqlite3.connect('items.db')
    conn.execute("INSERT INTO admins VALUES (?)", (int(update.message.text),))
    conn.commit()
    conn.close()
    await update.message.reply_text("✅ Admin qo'shildi!")
    return ConversationHandler.END

# --- ASOSIY HANDLERS ---
if __name__ == '__main__':
    Thread(target=run_flask).start()
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(add_start, pattern='add_item')],
        states={CATEGORY: [CallbackQueryHandler(select_cat, pattern='^selcat_|^new_cat$'), MessageHandler(filters.TEXT, get_cat_name)],
                NAME: [MessageHandler(filters.TEXT, get_name)], PRICE: [MessageHandler(filters.TEXT, get_price)],
                DESC: [MessageHandler(filters.TEXT, get_desc)], IMAGE: [MessageHandler(filters.PHOTO, get_image)]},
        fallbacks=[CommandHandler("start", start)]))

    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(checkout_start, pattern='checkout')],
        states={PHONE: [MessageHandler(filters.TEXT, get_phone)]}, fallbacks=[CommandHandler("start", start)]))

    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(reply_start, pattern='^reply_')],
        states={REPLY: [MessageHandler(filters.TEXT, send_reply)]}, fallbacks=[CommandHandler("start", start)]))

    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(add_admin_start, pattern='add_admin')],
        states={NEW_ADMIN: [MessageHandler(filters.TEXT, save_admin)]}, fallbacks=[CommandHandler("start", start)]))

    app.add_handler(CallbackQueryHandler(show_stats, pattern='show_stats'))
    app.add_handler(CallbackQueryHandler(del_item_menu, pattern='del_item'))
    app.add_handler(CallbackQueryHandler(perform_delete, pattern=r'^del_\d+$'))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT, handle_main))
    app.run_polling()
  
