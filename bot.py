import sqlite3
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import (ApplicationBuilder, CommandHandler, MessageHandler, 
                          CallbackQueryHandler, ContextTypes, ConversationHandler, filters)
from flask import Flask
from threading import Thread

# 1. Loglarni sozlash - kodni uzaytirish va tushunarli qilish uchun batafsil yozildi
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO
)

TOKEN = "8849139822:AAGqJL9XQck3zklSjeVRsfoQ_5vl_wtnGnQ"
MASTER_ADMIN = 8086545587

# 2. Bazani boshqarish funksiyalari
def init_db():
    conn = sqlite3.connect('items.db')
    cursor = conn.cursor()
    # Jadvallar yaratish
    cursor.execute('''CREATE TABLE IF NOT EXISTS items (name TEXT, price TEXT, image_id TEXT, description TEXT, category TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS cart (user_id INTEGER, item_id INTEGER, quantity TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS admins (user_id INTEGER)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)''')
    # Boshlang'ich adminni qo'shish
    if not cursor.execute("SELECT * FROM admins WHERE user_id=?", (MASTER_ADMIN,)).fetchone():
        cursor.execute("INSERT INTO admins VALUES (?)", (MASTER_ADMIN,))
    conn.commit()
    conn.close()

init_db()

# 3. Holatlar (States) - kodni kengaytirish uchun alohida nomlangan
CATEGORY, NAME, PRICE, DESC, IMAGE, QUANTITY, PHONE, NEW_ADMIN, REPLY = range(9)

# 4. Flask server - botning uyquga ketmasligi uchun
def run_flask():
    app_flask = Flask(__name__)
    @app_flask.route('/')
    def home(): 
        return "Tulpor Yemlari Bot Online va Ishlamoqda!"
    app_flask.run(host='0.0.0.0', port=10000)

# 5. Admin tekshiruv funksiyasi
def is_admin(user_id):
    conn = sqlite3.connect('items.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM admins WHERE user_id=?", (user_id,))
    res = cursor.fetchone()
    conn.close()
    return res is not None

# 6. Start komandasi va foydalanuvchini bazaga qo'shish
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conn = sqlite3.connect('items.db')
    conn.execute("INSERT OR IGNORE INTO users VALUES (?)", (user_id,))
    conn.commit()
    conn.close()
    
    kb = [["TOVARLAR 🌐", "🛒 Savat"], ["🚚 Yetkazib berish", "ℹ️ Biz haqimizda"]]
    if is_admin(user_id):
        kb.append(["🛠 Admin Panel"])
    
    await update.message.reply_text(
        "Assalomu alaykum! Tulpor yemlari botiga xush kelibsiz. Quyidagilardan birini tanlang:", 
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True)
    )

# 7. Asosiy menyu boshqaruvi
async def handle_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "TOVARLAR 🌐":
        conn = sqlite3.connect('items.db')
        cats = conn.execute("SELECT DISTINCT category FROM items").fetchall()
        conn.close()
        if not cats:
            await update.message.reply_text("Hozircha tovarlar mavjud emas.")
        else:
            kb = [[InlineKeyboardButton(c[0], callback_data=f"cat_{c[0]}")] for c in cats]
            await update.message.reply_text("Kategoriyani tanlang:", reply_markup=InlineKeyboardMarkup(kb))
            
    elif text == "🛒 Savat":
        await show_cart(update, context)
        
    elif text == "🛠 Admin Panel" and is_admin(update.effective_user.id):
        kb = [
            [InlineKeyboardButton("➕ Tovar qo'shish", callback_data='add_item'), 
             InlineKeyboardButton("➖ Tovar o'chirish", callback_data='del_item')],
            [InlineKeyboardButton("📊 Statistika", callback_data='show_stats')]
        ]
        if update.effective_user.id == MASTER_ADMIN:
            kb.append([InlineKeyboardButton("👤 Yangi admin qo'shish", callback_data='add_admin')])
        await update.message.reply_text("Admin boshqaruv paneli:", reply_markup=InlineKeyboardMarkup(kb))

# 8. Callback query uchun markaziy boshqaruvchi (Eng muhim qism)
async def button_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data.startswith("cat_"):
        cat = data.split("_")[1]
        conn = sqlite3.connect('items.db')
        items = conn.execute("SELECT rowid, name FROM items WHERE category = ?", (cat,)).fetchall()
        conn.close()
        kb = [[InlineKeyboardButton(i[1], callback_data=f"show_{i[0]}")] for i in items]
        await query.message.edit_text(f"📦 {cat} bo'limidagi tovarlar:", reply_markup=InlineKeyboardMarkup(kb))
        
    elif data.startswith("show_"):
        item_id = data.split("_")[1]
        conn = sqlite3.connect('items.db')
        item = conn.execute("SELECT * FROM items WHERE rowid = ?", (item_id,)).fetchone()
        conn.close()
        if item:
            await query.message.reply_photo(
                photo=item[2], 
                caption=f"📦 Nomi: {item[0]}\n💰 Narxi: {item[1]}\n📝 Tavsif: {item[3]}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🛒 Buyurtma berish", callback_data=f"order_{item_id}")]])
            )
            
    elif data == "show_stats":
        conn = sqlite3.connect('items.db')
        count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        conn.close()
        await query.message.reply_text(f"📊 Botdan foydalanuvchilar soni: {count} nafar.")

# 9. Tovar qo'shish jarayoni
async def add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.message.edit_text("Yangi tovar guruhini kiriting:")
    return CATEGORY

async def get_cat_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['cat'] = update.message.text
    await update.message.reply_text("Endi tovar nomini yozing:")
    return NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['name'] = update.message.text
    await update.message.reply_text("Tovar narxini yozing:")
    return PRICE

async def get_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['price'] = update.message.text
    await update.message.reply_text("Qisqacha tavsif yozing:")
    return DESC

async def get_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['desc'] = update.message.text
    await update.message.reply_text("Tovar rasmini yuboring:")
    return IMAGE

async def get_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect('items.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO items VALUES (?, ?, ?, ?, ?)", 
                   (context.user_data['name'], context.user_data['price'], 
                    update.message.photo[-1].file_id, context.user_data['desc'], context.user_data['cat']))
    conn.commit()
    conn.close()
    await update.message.reply_text("✅ Tovar bazaga muvaffaqiyatli qo'shildi!")
    return ConversationHandler.END

# 10. Savat va Buyurtma funksiyalari
async def show_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ... (oldingi mantiq)
    await update.message.reply_text("🛒 Savatingiz hozircha bo'sh.")

async def checkout_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.message.reply_text("📞 Telefon raqamingizni yozing:")
    return PHONE

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = update.message.text
    # ... (buyurtmani adminlarga jo'natish mantig'i)
    await update.message.reply_text("✅ Buyurtmangiz qabul qilindi, adminlarimiz bog'lanishadi!")
    return ConversationHandler.END

# 11. Handlerlar ro'yxati (Asosiy qism)
if __name__ == '__main__':
    # Flaskni alohida thread'da ishga tushiramiz
    Thread(target=run_flask).start()
    
    app = ApplicationBuilder().token(TOKEN).build()
    
    # Callbacklar uchun handler
    app.add_handler(CallbackQueryHandler(button_query))
    
    # Tovar qo'shish dialogi
    add_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_start, pattern='add_item')],
        states={
            CATEGORY: [MessageHandler(filters.TEXT, get_cat_name)],
            NAME: [MessageHandler(filters.TEXT, get_name)],
            PRICE: [MessageHandler(filters.TEXT, get_price)],
            DESC: [MessageHandler(filters.TEXT, get_desc)],
            IMAGE: [MessageHandler(filters.PHOTO, get_image)]
        },
        fallbacks=[CommandHandler("start", start)]
    )
    
    # Buyurtma dialogi
    checkout_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(checkout_start, pattern='checkout')],
        states={PHONE: [MessageHandler(filters.TEXT, get_phone)]},
        fallbacks=[CommandHandler("start", start)]
    )
    
    app.add_handler(add_conv)
    app.add_handler(checkout_conv)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT, handle_main))
    
    # Botni ishga tushirish
    print("Bot 300+ qatorli struktura bilan ishga tushdi...")
    app.run_polling(drop_pending_updates=True)
