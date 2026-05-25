import sqlite3
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import (ApplicationBuilder, CommandHandler, MessageHandler, 
                          CallbackQueryHandler, ContextTypes, ConversationHandler, filters)

# --- SOZLAMALAR ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
TOKEN = "8849139822:AAGMl30M3Xm-IOxiWE6n8BS8NVOQyfhACGw"
ADMIN_ID = 8086545587

# --- MA'LUMOTLAR BAZASI ---
def init_db():
    conn = sqlite3.connect('items.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS items 
                      (name TEXT, price TEXT, image_id TEXT, description TEXT)''')
    conn.commit()
    conn.close()

init_db()

# --- HOLATLAR ---
NAME, PRICE, IMAGE, DESC = range(4)

# --- FUNKSIYALAR ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    kb = [["TOVARLAR 🌐", "🛒 Savat"], ["🚚 Yetkazib berish", "ℹ️ Biz haqimizda"]]
    if user.id == ADMIN_ID: kb.append(["🛠 Admin Panel"])
    welcome_text = f"Assalomu alaykum, {user.first_name}! Tulpor yemlari botiga xush kelibsiz. Biz sizga eng sifatli yem mahsulotlarini taklif qilamiz."
    await update.message.reply_text(welcome_text, reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))

async def handle_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "TOVARLAR 🌐":
        conn = sqlite3.connect('items.db')
        items = conn.execute("SELECT rowid, name FROM items").fetchall()
        conn.close()
        if not items: await update.message.reply_text("Hozircha tovarlar mavjud emas.")
        else:
            kb = [[InlineKeyboardButton(i[1], callback_data=f"show_{i[0]}")] for i in items]
            await update.message.reply_text("📦 *Bizning tovarlar:*", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(kb))
    
    elif text == "🛠 Admin Panel" and update.effective_user.id == ADMIN_ID:
        kb = [[InlineKeyboardButton("➕ Tovar qo'shish", callback_data='add_item'),
               InlineKeyboardButton("➖ Tovar o'chirish", callback_data='del_item')]]
        await update.message.reply_text("Admin boshqaruv paneli:", reply_markup=InlineKeyboardMarkup(kb))
    
    elif text == "ℹ️ Biz haqimizda": 
        await update.message.reply_text("Tulpor yemlari - 5 yillik tajriba! Biz sifatni birinchi o'ringa qo'yamiz. 🐎")

# --- ADMIN JARAYONLARI ---
async def add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.message.reply_text("Yangi tovar nomini kiriting:")
    return NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['name'] = update.message.text
    await update.message.reply_text("Tovar narxini yozing (masalan: 50000):")
    return PRICE

async def get_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['price'] = update.message.text
    await update.message.reply_text("Tovarga qisqacha tavsif yozing:")
    return DESC

async def get_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['desc'] = update.message.text
    await update.message.reply_text("Endi rasmni yuboring:")
    return IMAGE

async def get_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    img_id = update.message.photo[-1].file_id
    conn = sqlite3.connect('items.db')
    conn.execute("INSERT INTO items VALUES (?, ?, ?, ?)", 
                 (context.user_data['name'], context.user_data['price'], img_id, context.user_data['desc']))
    conn.commit()
    conn.close()
    await update.message.reply_text("✅ Tovar muvaffaqiyatli bazaga qo'shildi!")
    return ConversationHandler.END

# --- O'CHIRISH VA KO'RSATISH ---
async def delete_item_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    conn = sqlite3.connect('items.db')
    items = conn.execute("SELECT rowid, name FROM items").fetchall()
    conn.close()
    if not items: await query.message.reply_text("O'chirish uchun tovarlar mavjud emas.")
    else:
        kb = [[InlineKeyboardButton(f"❌ {i[1]}", callback_data=f"del_{i[0]}")] for i in items]
        await query.message.reply_text("O'chirish uchun tovarni tanlang:", reply_markup=InlineKeyboardMarkup(kb))

async def perform_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    item_id = query.data.split("_")[1]
    conn = sqlite3.connect('items.db')
    conn.execute("DELETE FROM items WHERE rowid = ?", (item_id,))
    conn.commit()
    conn.close()
    await query.answer("Tovar o'chirildi!")
    await query.message.edit_text("✅ Tanlangan tovar muvaffaqiyatli o'chirildi.")

async def show_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    item_id = query.data.split("_")[1]
    conn = sqlite3.connect('items.db')
    item = conn.execute("SELECT * FROM items WHERE rowid = ?", (item_id,)).fetchone()
    conn.close()
    await query.message.reply_photo(photo=item[2], caption=f"📦 Nomi: {item[0]}\n💰 Narxi: {item[1]} so'm\n📝 Tavsif: {item[3]}")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    
    conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_start, pattern='add_item')],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_price)],
            DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_desc)],
            IMAGE: [MessageHandler(filters.PHOTO, get_image)]
        },
        fallbacks=[CommandHandler("start", start)]
    )
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(delete_item_menu, pattern='del_item'))
    app.add_handler(CallbackQueryHandler(perform_delete, pattern=r'^del_\d+$'))
    app.add_handler(CallbackQueryHandler(show_item, pattern=r'^show_\d+$'))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_main))
    
    print("Bot 24/7 rejimida ishlamoqda...")
    app.run_polling()
      
