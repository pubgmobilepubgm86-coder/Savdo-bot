import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import (ApplicationBuilder, CommandHandler, MessageHandler, 
                          CallbackQueryHandler, ContextTypes, ConversationHandler, filters)

TOKEN = "8849139822:AAGMl30M3Xm-IOxiWE6n8BS8NVOQyfhACGw"
ADMIN_ID = 8086545587

def init_db():
    conn = sqlite3.connect('items.db')
    conn.execute('CREATE TABLE IF NOT EXISTS items (name TEXT, price TEXT, image_id TEXT)')
    conn.commit()
    conn.close()

init_db()

NAME, PRICE, IMAGE = range(3)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [["TOVARLAR 🌐", "🛒 Savat"], ["🚚 Yetkazib berish", "ℹ️ Biz haqimizda"]]
    if update.effective_user.id == ADMIN_ID: kb.append(["🛠 Admin Panel"])
    await update.message.reply_text("Assalomu alaykum! Tulpor yemlari botiga xush kelibsiz.", 
                                    reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))

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
        await update.message.reply_text("Assalomu alaykum! Biz Tulpor savdo markazi. 5 yildan beri hizmat ko'rsatamiz. Bizning tovarlar sifati a'lo, narxi esa hamyonbop. Sizlarni do'konimizda kutib qolamiz! 🐎🌐")
    elif text == "🛒 Savat": await update.message.reply_text("🛒 Savat bo'sh.")
    elif text == "🚚 Yetkazib berish": await update.message.reply_text("🚚 Yetkazib berish shartlari: Toshkent bo'ylab.")

# --- TOVAR QO'SHISH ---
async def add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text("Tovar nomini kiriting:")
    return NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['name'] = update.message.text
    await update.message.reply_text("Narxini kiriting:")
    return PRICE

async def get_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['price'] = update.message.text
    await update.message.reply_text("Rasmni yuboring:")
    return IMAGE

async def get_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    img_id = update.message.photo[-1].file_id
    conn = sqlite3.connect('items.db')
    conn.execute("INSERT INTO items VALUES (?, ?, ?)", (context.user_data['name'], context.user_data['price'], img_id))
    conn.commit()
    conn.close()
    await update.message.reply_text("✅ Tovar qo'shildi!")
    return ConversationHandler.END

# --- TOVAR O'CHIRISH ---
async def delete_item_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    conn = sqlite3.connect('items.db')
    items = conn.execute("SELECT rowid, name FROM items").fetchall()
    conn.close()
    if not items: await query.message.reply_text("O'chirish uchun tovarlar yo'q.")
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
    await query.message.edit_text("✅ Tovar muvaffaqiyatli o'chirildi.")

# --- KO'RSATISH ---
async def show_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    item_id = query.data.split("_")[1]
    conn = sqlite3.connect('items.db')
    item = conn.execute("SELECT * FROM items WHERE rowid = ?", (item_id,)).fetchone()
    conn.close()
    await query.message.reply_photo(photo=item[2], caption=f"📦 Nomi: {item[0]}\n💰 Narxi: {item[1]} so'm")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    conv = ConversationHandler(entry_points=[CallbackQueryHandler(add_start, pattern='add_item')],
        states={NAME: [MessageHandler(filters.TEXT, get_name)],
                PRICE: [MessageHandler(filters.TEXT, get_price)],
                IMAGE: [MessageHandler(filters.PHOTO, get_image)]}, fallbacks=[])
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(delete_item_menu, pattern='del_item'))
    app.add_handler(CallbackQueryHandler(perform_delete, pattern=r'^del_\d+$'))
    app.add_handler(CallbackQueryHandler(show_item, pattern=r'^show_\d+$'))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_main))
    app.run_polling()
      
