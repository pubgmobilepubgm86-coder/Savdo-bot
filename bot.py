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
ADMIN_ID = 8086545587

def init_db():
    conn = sqlite3.connect('items.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS items (name TEXT, price TEXT, image_id TEXT, description TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS cart (user_id INTEGER, item_id INTEGER, quantity TEXT)''')
    conn.commit()
    conn.close()

init_db()

NAME, PRICE, DESC, IMAGE, QUANTITY = range(5)

# Flask serveri (Render uchun)
def run_flask():
    app_flask = Flask(__name__)
    @app_flask.route('/')
    def home(): return "Bot ishlayapti!"
    app_flask.run(host='0.0.0.0', port=10000)

# Funksiyalar
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [["TOVARLAR 🌐", "🛒 Savat"], ["🚚 Yetkazib berish", "ℹ️ Biz haqimizda"]]
    if update.effective_user.id == ADMIN_ID: kb.append(["🛠 Admin Panel"])
    await update.message.reply_text("Assalomu alaykum!", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))

async def handle_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "TOVARLAR 🌐":
        conn = sqlite3.connect('items.db')
        items = conn.execute("SELECT rowid, name FROM items").fetchall()
        conn.close()
        if not items: await update.message.reply_text("Hozircha tovarlar yo'q.")
        else:
            kb = [[InlineKeyboardButton(i[1], callback_data=f"show_{i[0]}")] for i in items]
            await update.message.reply_text("📦 Tovar tanlang:", reply_markup=InlineKeyboardMarkup(kb))
    elif text == "🛒 Savat":
        await show_cart(update, context)
    elif text == "🛠 Admin Panel" and update.effective_user.id == ADMIN_ID:
        kb = [[InlineKeyboardButton("➕ Tovar qo'shish", callback_data='add_item')],
              [InlineKeyboardButton("➖ Tovar o'chirish", callback_data='del_item')]]
        await update.message.reply_text("Admin:", reply_markup=InlineKeyboardMarkup(kb))

async def show_cart(update, context):
    conn = sqlite3.connect('items.db')
    cart = conn.execute("SELECT i.name, c.quantity FROM cart c JOIN items i ON c.item_id = i.rowid WHERE c.user_id = ?", (update.effective_user.id,)).fetchall()
    conn.close()
    if not cart: await update.message.reply_text("🛒 Savat bo'sh.")
    else:
        text = "🛒 Savatingiz:\n" + "\n".join([f"{i[0]} - {i[1]}" for i in cart])
        await update.message.reply_text(text)

# Tovar qo'shish jarayoni
async def add_start(update, context):
    await update.callback_query.message.reply_text("Tovar nomini yozing:")
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
    conn.execute("INSERT INTO items VALUES (?, ?, ?, ?)", (context.user_data['name'], context.user_data['price'], update.message.photo[-1].file_id, context.user_data['desc']))
    conn.commit()
    conn.close()
    await update.message.reply_text("✅ Tovar qo'shildi!")
    return ConversationHandler.END

# Buyurtma
async def show_item(update, context):
    item_id = update.callback_query.data.split("_")[1]
    context.user_data['item_id'] = item_id
    conn = sqlite3.connect('items.db')
    item = conn.execute("SELECT * FROM items WHERE rowid = ?", (item_id,)).fetchone()
    conn.close()
    await update.callback_query.message.reply_photo(item[2], caption=f"{item[0]}\nNarxi: {item[1]}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🛒 Buyurtma berish", callback_data=f"order_{item_id}")]]))

async def order_start(update, context):
    await update.callback_query.message.reply_text("Nechta kerak?")
    return QUANTITY

async def get_quantity(update, context):
    conn = sqlite3.connect('items.db')
    conn.execute("INSERT INTO cart VALUES (?, ?, ?)", (update.effective_user.id, context.user_data['item_id'], update.message.text))
    conn.commit()
    conn.close()
    await update.message.reply_text("✅ Savatga qo'shildi!")
    return ConversationHandler.END

if __name__ == '__main__':
    Thread(target=run_flask).start()
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(add_start, pattern='add_item')],
        states={NAME: [MessageHandler(filters.TEXT, get_name)], PRICE: [MessageHandler(filters.TEXT, get_price)],
                DESC: [MessageHandler(filters.TEXT, get_desc)], IMAGE: [MessageHandler(filters.PHOTO, get_image)]},
        fallbacks=[CommandHandler("start", start)]))

    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(order_start, pattern=r'^order_\d+$')],
        states={QUANTITY: [MessageHandler(filters.TEXT, get_quantity)]},
        fallbacks=[CommandHandler("start", start)]))

    app.add_handler(CallbackQueryHandler(show_item, pattern=r'^show_\d+$'))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT, handle_main))
    app.run_polling()
      
