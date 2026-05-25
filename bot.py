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
DB_NAME = 'items.db'

# ==========================================
# 2. MA'LUMOTLAR BAZASI (Savat va Foydalanuvchilar to'liq)
# ==========================================
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS items (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, price TEXT, image_id TEXT, description TEXT, category TEXT)''')
    # Savat jadvali (user_id, item_id, quantity)
    cursor.execute('''CREATE TABLE IF NOT EXISTS cart (user_id INTEGER, item_id INTEGER, quantity INTEGER)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS admins (user_id INTEGER UNIQUE)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)''')
    cursor.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (MASTER_ADMIN,))
    conn.commit()
    conn.close()

init_db()

# Baza yordamchi funksiyalari
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

def get_all_users():
    conn = sqlite3.connect(DB_NAME)
    users = conn.execute("SELECT user_id FROM users").fetchall()
    conn.close()
    return [user[0] for user in users]

def add_to_cart(user_id, item_id):
    conn = sqlite3.connect(DB_NAME)
    existing = conn.execute("SELECT quantity FROM cart WHERE user_id=? AND item_id=?", (user_id, item_id)).fetchone()
    if existing:
        conn.execute("UPDATE cart SET quantity = quantity + 1 WHERE user_id=? AND item_id=?", (user_id, item_id))
    else:
        conn.execute("INSERT INTO cart (user_id, item_id, quantity) VALUES (?, ?, 1)", (user_id, item_id))
    conn.commit()
    conn.close()

def get_cart_items(user_id):
    conn = sqlite3.connect(DB_NAME)
    items = conn.execute(
        "SELECT items.id, items.name, items.price, cart.quantity FROM cart JOIN items ON cart.item_id = items.id WHERE cart.user_id=?", 
        (user_id,)
    ).fetchall()
    conn.close()
    return items

def clear_cart(user_id):
    conn = sqlite3.connect(DB_NAME)
    conn.execute("DELETE FROM cart WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

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

# ==========================================
# 3. CONVERSATION STATES (HOLATLAR)
# ==========================================
ADD_CAT, ADD_NAME, ADD_PRICE, ADD_DESC, ADD_IMAGE = range(5)
ADD_ADMIN_ID = 5
CHECKOUT_PHONE = 6
ADMIN_REPLY_TEXT = 7
BROADCAST_TEXT = 8  # Hamma foydalanuvchilarga xabar yuborish bosqichi

# Har bir xabarga avtomatik qo'shiladigan eslatma matni generatori
def get_footer(current_function_info):
    return f"\n\n---\nℹ️ *Hozirgi bo'lim:* {current_function_info}\n🛒 *Savatni boshqarish:* Pastdagi '🛒 Savat' tugmasi orqali tovarlarni rasmiylashtirishingiz mumkin."

# ==========================================
# 4. SERVER UPTIME (FLASK)
# ==========================================
def run_flask():
    app_flask = Flask(__name__)
    @app_flask.route('/')
    def home(): return "Tulpor Yemlari Bot Markazi Aktiv!"
    app_flask.run(host='0.0.0.0', port=10000)

# ==========================================
# 5. ASOSIY MENYU HANDLERLARI
# ==========================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_user_db(user.id)
    
    kb = [["TOVARLAR 🌐", "🛒 Savat"], ["🚚 Yetkazib berish", "ℹ️ Biz haqimizda"]]
    if is_admin(user.id): kb.append(["🛠 Admin Panel"])
        
    info = "Botning asosiy bosh sahifasi (Bosh menyu)."
    await update.message.reply_text(
        f"Assalomu alaykum, {user.first_name}! Tulpor yemlari botiga xush kelibsiz." + get_footer(info), 
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True),
        parse_mode='Markdown'
    )

async def handle_main_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    
    if text == "TOVARLAR 🌐":
        cats = get_categories()
        info = "Tovarlar katalogi guruhlari ro'yxati."
        if not cats:
            await update.message.reply_text("Hozircha tovarlar qo'shilmagan." + get_footer(info), parse_mode='Markdown')
        else:
            kb = [[InlineKeyboardButton(c, callback_data=f"cat_{c}")] for c in cats]
            await update.message.reply_text("Guruhni tanlang:", reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')
            
    elif text == "🛒 Savat":
        cart_items = get_cart_items(user_id)
        info = "Sizning savatingiz va buyurtma berish oynasi."
        if not cart_items:
            await update.message.reply_text("🛒 Savatingiz hozircha bo'sh. Tovarlar bo'limidan mahsulot qo'shing!" + get_footer(info), parse_mode='Markdown')
        else:
            msg = "🛒 *Sizning savatingizda:*\n\n"
            total_price = 0
            for item_id, name, price, qty in cart_items:
                msg += f"🔸 *{name}* - {qty} ta x {price}\n"
            
            kb = [
                [InlineKeyboardButton("🚖 Buyurtmani rasmiylashtirish", callback_data="checkout_start")],
                [InlineKeyboardButton("🗑 Savatni tozalash", callback_data="clear_cart")]
            ]
            await update.message.reply_text(msg + get_footer(info), reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')
            
    elif text == "🚚 Yetkazib berish":
        info = "Yetkazib berish va aloqa ma'lumotlari."
        await update.message.reply_text("Bizlar chortoq boʻyicha dastafka xizmatimiz bor\n+998930423150" + get_footer(info), parse_mode='Markdown')
        
    elif text == "ℹ️ Biz haqimizda":
        info = "Kompaniya haqida ma'lumot."
        await update.message.reply_text("Tulpor yemlari - sifat va barakali mahsulotlar lidersi!" + get_footer(info), parse_mode='Markdown')
        
    elif text == "🛠 Admin Panel" and is_admin(user_id):
        info = "Do'kon ma'murlari uchun boshqaruv paneli."
        kb = [
            [InlineKeyboardButton("➕ Yangi tovar qo'shish", callback_data='add_item'), InlineKeyboardButton("裁 Tovar o'chirish", callback_data='del_item')],
            [InlineKeyboardButton("👤 Yangi admin qo'shish", callback_data='add_admin'), InlineKeyboardButton("📢 Barchaga xabar yozish", callback_data='broadcast_start')],
            [InlineKeyboardButton("📊 Statistika", callback_data='show_stats')]
        ]
        await update.message.reply_text("🛠 Admin boshqaruv paneli:", reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')

# ==========================================
# 6. MARKAZIY CALLBACK ROUTER (TUGMALAR)
# ==========================================
async def button_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id
    
    if data.startswith("cat_"):
        cat_name = data.replace("cat_", "")
        items = get_items_by_cat(cat_name)
        info = f"{cat_name} guruhidagi tovarlar ro'yxati ko'rilmoqda."
        if items:
            kb = [[InlineKeyboardButton(i[1], callback_data=f"show_{i[0]}")] for i in items]
            await query.message.edit_text(f"📦 {cat_name} guruhidagi tovarlar:" + get_footer(info), reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')
        else:
            await query.message.edit_text("Bu guruhda tovar topilmadi." + get_footer(info), parse_mode='Markdown')
            
    elif data.startswith("show_"):
        item_id = int(data.replace("show_", ""))
        item = get_item_details(item_id)
        info = "Tanlangan tovar tafsilotlari va savatga qo'shish oynasi."
        if item:
            name, price, image_id, desc, category = item
            caption = f"📌 *Nomi:* {name}\n💰 *Narxi:* {price}\n📝 *Ma'lumot:* {desc}" + get_footer(info)
            kb = [[InlineKeyboardButton("📥 Savatga qo'shish", callback_data=f"add_to_cart_{item_id}")]]
            await query.message.reply_photo(photo=image_id, caption=caption, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(kb))
            
    elif data.startswith("add_to_cart_"):
        item_id = int(data.replace("add_to_cart_", ""))
        add_to_cart(user_id, item_id)
        info = "Mahsulot savatga muvaffaqiyatli qo'shildi."
        await query.message.reply_text("✅ Mahsulot savatingizga qo'shildi! Savat menyusiga o'tib buyurtma berishingiz mumkin." + get_footer(info), parse_mode='Markdown')
        
    elif data == "clear_cart":
        clear_cart(user_id)
        info = "Savat muvaffaqiyatli tozalandi."
        await query.message.edit_text("🗑 Savatingiz butunlay tozalandi!" + get_footer(info), parse_mode='Markdown')
        
    elif data == "show_stats" and is_admin(user_id):
        conn = sqlite3.connect(DB_NAME)
        count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        conn.close()
        await query.message.reply_text(f"📊 Jami foydalanuvchilar soni: {count} ta.")
        
    elif data == "del_item" and is_admin(user_id):
        conn = sqlite3.connect(DB_NAME)
        all_items = conn.execute("SELECT id, name FROM items").fetchall()
        conn.close()
        kb = [[InlineKeyboardButton(f"❌ {i[1]}", callback_data=f"del_{i[0]}")] for i in all_items]
        await query.message.reply_text("O'chirish uchun tovarni tanlang:", reply_markup=InlineKeyboardMarkup(kb))
            
    elif data.startswith("del_") and is_admin(user_id):
        item_id = int(data.replace("del_", ""))
        delete_item_db(item_id)
        await query.message.edit_text("✅ Tovar muvaffaqiyatli o'chirildi.")

# ==========================================
# 7. CONVERSATION: TOVAR QO'SHISH LOGIKASI
# ==========================================
async def add_item_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if is_admin(query.from_user.id):
        await query.message.reply_text("Yangi tovar guruhini (kategoriyasini) yozing:")
        return ADD_CAT
    return ConversationHandler.END

async def get_item_cat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['cat'] = update.message.text
    await update.message.reply_text("Tovar nomini yozing:")
    return ADD_NAME

async def get_item_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['name'] = update.message.text
    await update.message.reply_text("Tovar narxini yozing:")
    return ADD_PRICE

async def get_item_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['price'] = update.message.text
    await update.message.reply_text("Tovar haqida batafsil ma'lumot yozing:")
    return ADD_DESC

async def get_item_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['desc'] = update.message.text
    await update.message.reply_text("Tovar rasmini yuboring:")
    return ADD_IMAGE

async def get_item_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo_id = update.message.photo[-1].file_id
    cat = context.user_data['cat']
    name = context.user_data['name']
    price = context.user_data['price']
    desc = context.user_data['desc']
    
    conn = sqlite3.connect(DB_NAME)
    conn.execute("INSERT INTO items (name, price, image_id, description, category) VALUES (?, ?, ?, ?, ?)", (name, price, photo_id, desc, cat))
    conn.commit()
    conn.close()
    await update.message.reply_text("✅ Yangi tovar muvaffaqiyatli qo'shildi!")
    return ConversationHandler.END

# ==========================================
# 8. CONVERSATION: YANGI ADMIN QO'SHISH
# ==========================================
async def add_admin_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if is_admin(query.from_user.id):
        await query.message.reply_text("Yangi admin Telegram ID raqamini kiriting:")
        return ADD_ADMIN_ID
    return ConversationHandler.END

async def get_new_admin_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        new_id = int(update.message.text)
        add_admin_db(new_id)
        await update.message.reply_text(f"✅ ID {new_id} egasi muvaffaqiyatli admin bo'ldi!")
    except ValueError:
        await update.message.reply_text("Faqat raqamlardan iborat ID kiriting.")
    return ConversationHandler.END

# ==========================================
# 9. CONVERSATION: BUYURTMANI RASMIYLASHTIRISH
# ==========================================
async def checkout_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text("📞 Buyurtmani tasdiqlash va aloqa o'rnatish uchun telefon raqamingizni kiriting:")
    return CHECKOUT_PHONE

async def get_checkout_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = update.message.text
    user = update.effective_user
    user_id = user.id
    
    cart_items = get_cart_items(user_id)
    if not cart_items:
        await update.message.reply_text("Sizning savatingiz bo'sh bo'lgani sababli buyurtma bekor qilindi.")
        return ConversationHandler.END
        
    # Savat tarkibini xabarga yig'ish
    cart_info = ""
    for item_id, name, price, qty in cart_items:
        cart_info += f"📦 *{name}* - {qty} ta (Narxi: {price})\n"
        
    msg = (
        f"🔔 *YANGI BUYURTMA KELDI!*\n\n"
        f"👤 *Mijoz:* {user.full_name}\n"
        f"📞 *Tel:* {phone}\n"
        f"🆔 *Mijoz ID:* `{user.id}`\n"
        f"💬 *Username:* @{user.username if user.username else 'Yo oq'}\n\n"
        f"🛒 *Savat tarkibi:*\n{cart_info}"
    )
    
    kb = [[InlineKeyboardButton("📩 Javob qaytarish", callback_data=f"reply_{user.id}")]]
    
    # Barcha adminlarga xabar yetkazish
    admins = get_all_admins()
    for admin_id in admins:
        try:
            await context.bot.send_message(chat_id=admin_id, text=msg, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(kb))
        except Exception as e:
            logger.error(f"Xatolik: {e}")
            
    clear_cart(user_id)  # Buyurtma rasmiylashgach savat tozalanadi
    await update.message.reply_text("✅ Buyurtmangiz qabul qilindi va adminlarga yetkazildi! Savatingiz rasmiylashtirildi.")
    return ConversationHandler.END

# ==========================================
# 10. CONVERSATION: ADMIN JAVOB QAYTARISH
# ==========================================
async def admin_reply_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    target_user_id = int(query.data.split("_")[1])
    context.user_data['reply_target_id'] = target_user_id
    await query.message.reply_text("📝 Mijozga yuboriladigan javob xabaringizni yozing:")
    return ADMIN_REPLY_TEXT

async def admin_send_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply_text = update.message.text
    target_id = context.user_data.get('reply_target_id')
    try:
        user_msg = f"✉️ *Adminlardan kelgan javob xabari:*\n\n{reply_text}"
        await context.bot.send_message(chat_id=target_id, text=user_msg, parse_mode='Markdown')
        await update.message.reply_text("✅ Xabaringiz mijozga bot orqali yetkazildi!")
    except Exception as e:
        await update.message.reply_text(f"❌ Xabar yuborilmadi: {e}")
    return ConversationHandler.END

# ==========================================
# 11. CONVERSATION: BARCHAGA REKLAMA/XABAR (RASSILKA)
# ==========================================
async def broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if is_admin(query.from_user.id):
        await query.message.reply_text("📢 Botning barcha foydalanuvchilariga yuboriladigan umumiy xabar yoki reklama matnini kiriting:")
        return BROADCAST_TEXT
    return ConversationHandler.END

async def send_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    broadcast_msg = update.message.text
    users = get_all_users()
    success = 0
    failed = 0
    
    await update.message.reply_text("🔄 Xabar barchaga yuborilmoqda, iltimos kuting...")
    
    for user_id in users:
        try:
            await context.bot.send_message(chat_id=user_id, text=f"📢 *Tulpor Yemlari rasmiy xabari:*\n\n{broadcast_msg}", parse_mode='Markdown')
            success += 1
        except Exception:
            failed += 1
            
    await update.message.reply_text(f"✅ Xabar yuborish tugadi!\n🟢 Yetkazildi: {success} ta\n🔴 Yetkazilmadi: {failed} ta (Botni bloklaganlar).")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Jarayon bekor qilindi.")
    return ConversationHandler.END

# ==========================================
# 12. MAIN PROGRAM
# ==========================================
def main():
    Thread(target=run_flask, daemon=True).start()
    app = ApplicationBuilder().token(TOKEN).build()
    
    # Conversations
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
        states={ADD_ADMIN_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_new_admi
