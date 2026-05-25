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

# Ma'lumotlar bazasi
def init_db():
    conn = sqlite3.connect('items.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS items 
                      (name TEXT, price TEXT, image_id TEXT, description TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS cart 
                      (user_id INTEGER, item_id INTEGER, quantity TEXT)''')
    conn.commit()
    conn.close()

init_db()

# Bosqichlar
NAME, PRICE, DESC, IMAGE, QUANTITY = range(5)

# --- FLASK SERVER (RENDER UCHUN) ---
app_flask = Flask(__name__)
@app_flask.route('/')
def home():
    return "Bot ishlayapti!"

def run_flask():
    app_flask.run(host='0.0.0.0', port=10000)

# --- FUNKSIYALAR ---
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
        if not items: await update.message.reply_text("Hozircha tovarlar yo'q.")
        else:
            kb = [[InlineKeyboardButton(i[1], callback_data=f"show_{i[0]}")] for i in items]
            await update.message.reply_text("📦 *Bizning tovarlar:*", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(kb))
    elif text == "🛒 Savat":
        await show_cart(update, context)
    elif text == "🛠 Admin Panel" and update.effective_user.id == ADMIN_ID:
        kb = [[InlineKeyboardButton("➕ Tovar qo'shish", callback_data='add_item'),
               InlineKeyboardButton("➖ Tovar o'chirish", callback_data='del_item')]]
        await update.message.reply_text("Admin boshqaruv paneli:", reply_markup=InlineKeyboardMarkup(kb))
    elif text == "ℹ️ Biz haqimizda": await update.message.reply_text("Tulpor yemlari - sifatli mahsulotlar!")

async def show_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conn = sqlite3.connect('items.db')
    cart_items = conn.execute("SELECT i.name, c.quantity FROM cart c JOIN items i ON c.item_id = i.rowid WHERE c.user_id = ?", (user_id,)).fetchall()
    conn.close()
    if not cart_items: await update.message.reply_text("🛒 Savatingiz bo'sh.")
    else:
        text = "🛒 *Sizning savatingiz:*\n\n"
        for idx, item in enumerate(cart_items, 1):
            text += f"{idx}. {item[0]} — *{item[1]}*\n"
        await update.message.reply_text(text, parse_mode='Markdown')

async def add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.message.reply_text("Tovar nomini kiriting:")
    return NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['name'] = update.message.text
    await update.message.reply_text("Narxini kiriting:")
    return PRICE

async def get_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['price'] = update.message.text
    await update.message.reply_text("Tavsifini yozing:")
    return DESC

async def get_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['desc'] = update.message.text
    await update.message.reply_text("Rasmni yuboring:")
    return IMAGE

async def get_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    img_id = update.message.photo[-1].file_id
    conn = sqlite3.connect('items.db')
    conn.execute("INSERT INTO items VALUES (?, ?, ?, ?)", (context.user_data['name'], context.user_data['price'], img_id, context.user_data['desc']))
    conn.commit()
    conn.close()
    await update.message.reply_text("✅ Tovar qo'shildi!")
    return ConversationHandler.END

async def show_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    item_id = query.data.split("_")[1]
    context.user_data['last_item_id'] = item_id
    conn = sqlite3.connect('items.db')
    item = conn.execute("SELECT * FROM items WHERE rowid = ?", (item_id,)).fetchone()
    conn.close()
    kb = [[InlineKeyboardButton("🛒 Buyurtma berish", callback_data=f"order_{item_id}")]]
    await query.message.reply_photo(photo=item[2], caption=f"📦 Nomi: {item[0]}\n💰 Narxi: {item[1]}\n📝 {item[3]}", reply_markup=InlineKeyboardMarkup(kb))

async def order_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text("Nechta yoki necha kg kerak:")
    return QUANTITY

async def get_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['last_qty'] = update.message.text
    kb = [[InlineKeyboardButton("✅ Savatga qo'shish", callback_data="add_to_cart")]]
    await update.message.reply_text(f"Tanlandi: {update.message.text}. Savatga qo'shasizmi?", reply_markup=InlineKeyboardMarkup(kb))
    return ConversationHandler.END

async def add_to_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    item_id = context.user_data.get('last_item_id')
    qty = context.user_data.get('last_qty')
    conn = sqlite3.connect('items.db')
    conn.execute("INSERT INTO cart VALUES (?, ?, ?)", (query.from_user.id, item_id, qty))
    conn.commit()
    conn.close()
    await query.answer("✅ Savatga qo'shildi!")
    await query.message.edit_text("✅ Tovar savatga muvaffaqiyatli tushdi!")

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
    await query.message.edit_text("✅ Tovar o'chirildi.")

if __name__ == '__main__':
    Thread(target=run_flask).start()
    app = ApplicationBuilder().token(TOKEN).build()
    
    add_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_start, pattern='add_item')],
        states={NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
                PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_price)],
                DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_desc)],
                IMAGE: [MessageHandler(filters.PHOTO, get_image)]},
        fallbacks=[CommandHandler("start", start)])

    order_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(order_start, pattern=r'^order_\d+$')],
        states={QUANTITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_quantity)]},
        fallbacks=[CommandHandler("start", start)])

    app.add_handler(CommandHandler("start", start))
    app.add_handler(add_conv)
    app.add_handler(order_conv)
    app.add_handler(CallbackQueryHandler(delete_item_menu, pattern='del_item'))
    app.add_handler(CallbackQueryHandler(perform_delete, pattern=r'^del_\d+$'))
    app.add_handler(CallbackQueryHandler(show_item, pattern=r'^show_\d+$'))
    app.add_handler(CallbackQueryHandler(add_to_cart, pattern='add_to_cart'))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_main))
    
    app.run_polling()
