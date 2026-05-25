import sqlite3
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (ApplicationBuilder, CommandHandler, MessageHandler, filters, 
                          CallbackQueryHandler, ContextTypes, ConversationHandler)

TOKEN = "8849139822:AAGMl30M3Xm-IOxiWE6n8BS8NVOQyfhACGw"
ADMIN_ID = 8086545587

# Ma'lumotlar bazasini sozlash
def init_db():
    conn = sqlite3.connect('items.db')
    conn.execute('CREATE TABLE IF NOT EXISTS items (name TEXT, price TEXT)')
    conn.commit()
    conn.close()

init_db()

# Bosqichlar
NAME, PRICE = range(2)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [["TOVARLAR 🌐", "🛒 Savat"], ["🚚 Yetkazib berish", "ℹ️ Biz haqimizda"]]
    if update.effective_user.id == ADMIN_ID: kb.append(["🛠 Admin Panel"])
    await update.message.reply_text("Assalomu alaykum! Tulpor yemlari botiga xush kelibsiz.", 
                                    reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))

async def handle_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "TOVARLAR 🌐":
        conn = sqlite3.connect('items.db')
        items = conn.execute("SELECT * FROM items").fetchall()
        conn.close()
        msg = "📦 *Bizning tovarlar:*\n\n" + "\n".join([f"• {i[0]} — {i[1]} so'm" for i in items]) if items else "Hozircha tovarlar yo'q."
        await update.message.reply_text(msg, parse_mode='Markdown')
    elif text == "🛠 Admin Panel" and update.effective_user.id == ADMIN_ID:
        kb = [[InlineKeyboardButton("➕ Tovar qo'shish", callback_data='add_item')]]
        await update.message.reply_text("Admin boshqaruv paneli:", reply_markup=InlineKeyboardMarkup(kb))
    elif text == "ℹ️ Biz haqimizda": await update.message.reply_text("Biz 5 yildan beri hizmatdamiz! 🐎🌐")
    elif text == "🛒 Savat": await update.message.reply_text("🛒 Savat bo'sh.")
    elif text == "🚚 Yetkazib berish": await update.message.reply_text("Toshkent bo'ylab.")

# Tovar qo'shish uchun suhbat
async def add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.message.reply_text("Tovar nomini kiriting:")
    return NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['name'] = update.message.text
    await update.message.reply_text("Narxini kiriting:")
    return PRICE

async def get_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = context.user_data['name']
    price = update.message.text
    conn = sqlite3.connect('items.db')
    conn.execute("INSERT INTO items VALUES (?, ?)", (name, price))
    conn.commit()
    conn.close()
    await update.message.reply_text("✅ Tovar qo'shildi!")
    return ConversationHandler.END

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_start, pattern='add_item')],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_price)]
        },
        fallbacks=[]
    )
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_main))
    app.run_polling()
