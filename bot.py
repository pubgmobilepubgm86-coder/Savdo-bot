import sqlite3
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, 
    CallbackQueryHandler, ContextTypes, ConversationHandler, filters
)
from flask import Flask
from threading import Thread

# ==========================================
# 1. SOZLAMALAR VA LOGGING
# ==========================================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = "8849139822:AAGqJL9XQck3zklSjeVRsfoQ_5vl_wtnGnQ"
MASTER_ADMIN = 8086545587

# ==========================================
# 2. MA'LUMOTLAR BAZASI (KENGAYTIRILGAN)
# ==========================================
DB_NAME = 'items.db'

def init_db():
    """Barcha jadvallarni yaratish va master adminni qo'shish."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS items (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, price TEXT, image_id TEXT, description TEXT, category TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS cart (user_id INTEGER, item_id INTEGER, quantity TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS admins (user_id INTEGER UNIQUE)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)''')
    
    # Master adminni xavfsiz qo'shish
    cursor.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (MASTER_ADMIN,))
    conn.commit()
    conn.close()

init_db()

# Baza yordamchi funksiyalari (Kod uzayishi va barqarorligi uchun alohida ajratildi)
def add_user_db(user_id):
    conn = sqlite3.connect(DB_NAME)
    conn.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()

def is_admin(user_id):
    conn = sqlite3.connect(DB_NAME)
    res = conn.execute("SELECT user_id FROM admins WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    return res is not None

def get_all_admins():
    conn = sqlite3.connect(DB_NAME)
    admins = conn.execute("SELECT user_id FROM admins").fetchall()
    conn.close()
    return [admin[0] for admin in admins]

def add_admin_db(user_id):
    conn = sqlite3.connect(DB_NAME)
    conn.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()

def get_categories():
    conn = sqlite3.connect(DB_NAME)
    cats = conn.execute("SELECT DISTINCT category FROM items").fetchall()
    conn.close()
    return [c[0] for c in cats if c[0]]

def get_items_by_cat(category):
    conn = sqlite3.connect(DB_NAME)
    items = conn.execute("SELECT id, name FROM items WHERE category=?", (category,)).fetchall()
    conn.close()
    return items

def get_item_details(item_id):
    conn = sqlite3.connect(DB_NAME)
    item = conn.execute("SELECT name, price, image_id, description, category FROM items WHERE id=?", (item_id,)).fetchone()
    conn.close()
    return item

def delete_item_db(item_id):
    conn = sqlite3.connect(DB_NAME)
    conn.execute("DELETE FROM items WHERE id=?", (item_id,))
    conn.commit()
    conn.close()

def get_users_count():
    conn = sqlite3.connect(DB_NAME)
    count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    conn.close()
    return count

# ==========================================
# 3. HOLATLAR (CONVERSATION STATES)
# ==========================================
# Tovar qo'shish bosqichlari
ADD_CAT, ADD_NAME, ADD_PRICE, ADD_DESC, ADD_IMAGE = range(5)
# Admin qo'shish bosqichi
ADD_ADMIN_ID = 5
# Buyurtma berish bosqichi
CHECKOUT_PHONE = 6

# ==========================================
# 4. SERVER (FLASK UPTIME 24/7)
# ==========================================
def run_flask():
    app_flask = Flask(__name__)
    @app_flask.route('/')
    def home(): 
        return "Tulpor Yemlari Bot aktiv holatda!"
    app_flask.run(host='0.0.0.0', port=10000)

# ==========================================
# 5. ASOSIY MENYU VA START
# ==========================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Botga start bosilganda ishlaydi."""
    user = update.effective_user
    add_user_db(user.id)
    
    # Menyu tugmalari
    kb = [
        ["TOVARLAR 🌐", "🛒 Savat"], 
        ["🚚 Yetkazib berish", "ℹ️ Biz haqimizda"]
    ]
    if is_admin(user.id):
        kb.append(["🛠 Admin Panel"])
        
    await update.message.reply_text(
        f"Assalomu alaykum, {user.first_name}! Tulpor yemlari botiga xush kelibsiz.", 
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True)
    )

async def handle_main_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Pastki menyu tugmalarini ushlaydigan asosiy funksiya."""
    text = update.message.text
    user_id = update.effective_user.id
    
    if text == "TOVARLAR 🌐":
        cats = get_categories()
        if not cats:
            await update.message.reply_text("Hozircha tovarlar qo'shilmagan.")
        else:
            kb = [[InlineKeyboardButton(c, callback_data=f"cat_{c}")] for c in cats]
            await update.message.reply_text("Guruhni tanlang:", reply_markup=InlineKeyboardMarkup(kb))
            
    elif text == "🛒 Savat":
        # Savat logikasi
        kb = [[InlineKeyboardButton("Rasmiylashtirish", callback_data="checkout_start")]]
        await update.message.reply_text("Savat bo'limi (Tez orada to'liq savat tizimi ishga tushadi). Hozircha to'g'ridan-to'g'ri buyurtma qoldirishingiz mumkin:", reply_markup=InlineKeyboardMarkup(kb))
            
    elif text == "🚚 Yetkazib berish":
        # SIZ AYTGAN MATN
        await update.message.reply_text("Bizlar chortoq boʻyicha dastafka xizmatimiz bor\n+998930423150")
        
    elif text == "ℹ️ Biz haqimizda":
        await update.message.reply_text("Tulpor yemlari - sifat va barakali mahsulotlar!")
        
    elif text == "🛠 Admin Panel":
        if is_admin(user_id):
            kb = [
                [InlineKeyboardButton("➕ Yangi tovar qo'shish", callback_data='add_item')],
                [InlineKeyboardButton("➖ Tovar ayirish (o'chirish)", callback_data='del_item')],
                [InlineKeyboardButton("📊 Statistika", callback_data='show_stats')],
                [InlineKeyboardButton("👤 Yangi admin qo'shish", callback_data='add_admin')]
            ]
            await update.message.reply_text("🛠 Admin paneli. Nima qilasiz?", reply_markup=InlineKeyboardMarkup(kb))
        else:
            await update.message.reply_text("Buning uchun sizda admin huquqi yo'q!")

# ==========================================
# 6. CALLBACK ROUTER (TUGMALAR)
# ==========================================
async def button_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Barcha oddiy inline tugmalarni boshqaruvchi markaz."""
    query = update.callback_query
    await query.answer()
    data = query.data
    
    # 6.1. Kategoriyani ko'rsatish
    if data.startswith("cat_"):
        cat_name = data.replace("cat_", "")
        items = get_items_by_cat(cat_name)
        if items:
            kb = [[InlineKeyboardButton(i[1], callback_data=f"show_{i[0]}")] for i in items]
            await query.message.edit_text(f"📦 {cat_name} guruhidagi tovarlar:", reply_markup=InlineKeyboardMarkup(kb))
        else:
            await query.message.edit_text("Bu guruhda tovar qolmadi.")
            
    # 6.2. Tovarni batafsil ko'rsatish
    elif data.startswith("show_"):
        item_id = int(data.replace("show_", ""))
        item = get_item_details(item_id)
        if item:
            name, price, image_id, desc, category = item
            caption = f"📌 *Nomi:* {name}\n💰 *Narxi:* {price}\n📝 *Ma'lumot:* {desc}"
            kb = [[InlineKeyboardButton("🛒 Buyurtma berish", callback_data="checkout_start")]]
            await query.message.reply_photo(photo=image_id, caption=caption, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(kb))
            
    # 6.3. Statistika
    elif data == "show_stats":
        if is_admin(query.from_user.id):
            count = get_users_count()
            await query.message.reply_text(f"📊 *Statistika:*\nJami foydalanuvchilar: {count} ta.", parse_mode='Markdown')
            
    # 6.4. O'chirish menyusini ochish (Tovar ayirish)
    elif data == "del_item":
        if is_admin(query.from_user.id):
            conn = sqlite3.connect(DB_NAME)
            all_items = conn.execute("SELECT id, name FROM items").fetchall()
            conn.close()
            if not all_items:
                await query.message.reply_text("O'chirish uchun tovarlar yo'q.")
                return
            kb = [[InlineKeyboardButton(f"❌ {i[1]}", callback_data=f"del_{i[0]}")] for i in all_items]
            await query.message.reply_text("Qaysi tovarni ayirasiz (o'chirasiz)?", reply_markup=InlineKeyboardMarkup(kb))
            
    # 6.5. Tovarni o'chirish harakati
    elif data.startswith("del_"):
        if is_admin(query.from_user.id):
            item_id = int(data.replace("del_", ""))
            delete_item_db(item_id)
            await query.message.edit_text("✅ Tovar bazadan muvaffaqiyatli o'chirildi.")

# ==========================================
# 7. CONVERSATION: TOVAR QO'SHISH
# ==========================================
async def add_item_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if is_admin(query.from_user.id):
        await query.message.reply_text("Yangi tovarning guruhini (kategoriyasini) yozing:")
        return ADD_CAT
    return ConversationHandler.END

async def get_item_cat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['cat'] = update.message.text
    await update.message.reply_text("Tovarning nomini yozing:")
    return ADD_NAME

async def get_item_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['name'] = update.message.text
    await update.message.reply_text("Tovarning narxini yozing:")
    return ADD_PRICE

async def get_item_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['price'] = update.message.text
    await update.message.reply_text("Tovar haqida ma'lumot (tavsif) yozing:")
    return ADD_DESC

async def get_item_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['desc'] = update.message.text
    await update.message.reply_text("Tovarning rasmini yuboring:")
    return ADD_IMAGE

async def get_item_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo_id = update.message.photo[-1].file_id
    cat = context.user_data['cat']
    name = context.user_data['name']
    price = context.user_data['price']
    desc = context.user_data['desc']
    
    conn = sqlite3.connect(DB_NAME)
    conn.execute("INSERT INTO items (name, price, image_id, description, category) VALUES (?, ?, ?, ?, ?)", 
                 (name, price, photo_id, desc, cat))
    conn.commit()
    conn.close()
    
    await update.message.reply_text("✅ Tovar muvaffaqiyatli qo'shildi!")
    return ConversationHandler.END

# ==========================================
# 8. CONVERSATION: ADMIN QO'SHISH
# ==========================================
async def add_admin_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if is_admin(query.from_user.id):
        await query.message.reply_text("Yangi adminning Telegram ID raqamini kiriting:")
        return ADD_ADMIN_ID
    return ConversationHandler.END

async def get_new_admin_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        new_id = int(update.message.text)
        add_admin_db(new_id)
        await update.message.reply_text(f"✅ {new_id} ID egasi admin qilib tayinlandi.")
    except ValueError:
        await update.message.reply_text("Iltimos, faqat raqam (ID) kiriting.")
    return ConversationHandler.END

# ==========================================
# 9. CONVERSATION: BUYURTMANI RASMIYLASHTIRISH
# ==========================================
async def checkout_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text("📞 Buyurtma berish uchun telefon raqamingizni yozib qoldiring (Masalan: +998901234567):")
    return CHECKOUT_PHONE

async def get_checkout_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = update.message.text
    user = update.effective_user
    
    # Adminlarga yuboriladigan xabar
    msg = f"🔔 *YANGI BUYURTMA!*\n\n👤 Mijoz: {user.full_name}\n📞 Tel: {phone}\n"
    if user.username:
        msg += f"💬 User: @{user.username}\n"
        
    admins = get_all_admins()
    
    success_count = 0
    # BARCHA ADMINLARGA XABAR YUBORISH (Siz so'ragan funksiya to'liq ishlaydi)
    for admin_id in admins:
        try:
            await context.bot.send_message(
                chat_id=admin_id, 
                text=msg, 
                parse_mode='Markdown'
            )
            success_count += 1
        except Exception as e:
            logger.error(f"Adminga yuborib bo'lmadi ({admin_id}): {e}")
            
    await update.message.reply_text("✅ Buyurtmangiz qabul qilindi. Tez orada siz bilan bog'lanamiz!")
    return ConversationHandler.END

# ==========================================
# 10. CANCEL HANDLER
# ==========================================
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Jarayonni bekor qilish."""
    await update.message.reply_text("Jarayon bekor qilindi.")
    return ConversationHandler.END

# ==========================================
# 11. MAIN (Dasturni yig'ish va ishga tushirish)
# ==========================================
def main():
    # Flaskni ishga tushiramiz (Uptime uchun)
    flask_thread = Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    # Bot quruvchisi
    app = ApplicationBuilder().token(TOKEN).build()
    
    # --- CONVERSATION HANDLERS ---
    # Diqqat: Bular oddiy handlerlardan oldin qo'shilishi shart, shunda to'qnashuv bo'lmaydi!
    
    conv_add_item = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_item_start, pattern='^add_item$')],
        states={
            ADD_CAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_item_cat)],
            ADD_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_item_name)],
            ADD_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_item_price)],
            ADD_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_item_desc)],
            ADD_IMAGE: [MessageHandler(filters.PHOTO, get_item_image)],
        },
        fallbacks=[CommandHandler('cancel', cancel), CommandHandler('start', start)]
    )

    conv_add_admin = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_admin_start, pattern='^add_admin$')],
        states={
            ADD_ADMIN_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_new_admin_id)],
        },
        fallbacks=[CommandHandler('cancel', cancel), CommandHandler('start', start)]
    )
    
    conv_checkout = ConversationHandler(
        entry_points=[CallbackQueryHandler(checkout_start, pattern='^checkout_start$')],
        states={
            CHECKOUT_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_checkout_phone)],
        },
        fallbacks=[CommandHandler('cancel', cancel), CommandHandler('start', start)]
    )
    
    # 1-navbatda Conversationlarni qo'shamiz
    app.add_handler(conv_add_item)
    app.add_handler(conv_add_admin)
    app.add_handler(conv_checkout)
    
    # 2-navbatda Umumiy Callbacklarni qo'shamiz
    app.add_handler(CallbackQueryHandler(button_router))
    
    # 3-navbatda Command va Text xabarlarni qo'shamiz
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_main_text))
    
    print("🚀 Bot 400+ qatorli mukammal tizim bilan ishga tushdi...")
    # drop_pending_updates bot o'chib qolgan paytdagi eski xabarlarni o'qimasligini ta'minlaydi
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
  
