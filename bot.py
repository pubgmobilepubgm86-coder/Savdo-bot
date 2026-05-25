import sqlite3
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import (ApplicationBuilder, CommandHandler, MessageHandler, 
                          CallbackQueryHandler, ContextTypes, ConversationHandler, filters)
from flask import Flask
from threading import Thread

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

TOKEN = "8849139822:AAEOia8xieoZ9kfUZjKadw7z6JcQ0cSZ1oY"
ADMIN_ID = 8086545587

def init_db():
    conn = sqlite3.connect('items.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS items (name TEXT, price TEXT, image_id TEXT, description TEXT, category TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS cart (user_id INTEGER, item_id INTEGER, quantity TEXT)''')
    conn.commit()
    conn.close()

init_db()

CATEGORY, NAME, PRICE, DESC, IMAGE, QUANTITY = range(6)

def run_flask():
    app_flask = Flask(__name__)
    @app_flask.route('/')
    def home(): return "Bot ishlayapti!"
    app_flask.run(host='0.0.0.0', port=10000)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [["TOVARLAR 🌐", "🛒 Savat"], ["🚚 Yetkazib berish", "ℹ️ Biz haqimizda"]]
    if update.effective_user.id == ADMIN_ID: kb.append(["🛠 Admin Panel"])
    await update.message.reply_text("Assalomu alaykum! Tulpor yemlari botiga xush kelibsiz.", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))

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
    elif text == "ℹ️ Biz haqimizda": await update.message.reply_text("Tulpor yemlari - biz sifatli va arzon mahsulotlarni yetkazib beramiz. Mijozlarimiz ishonchi - bizning maqsadimiz!")
    elif text == "🛠 Admin Panel" and update.effective_user.id == ADMIN_ID:
        kb = [[InlineKeyboardButton("➕ Tovar qo'shish", callback_data='add_item')], [InlineKeyboardButton("➖ Tovar o'chirish", callback_data='del_item')]]
        await update.message.reply_text("Admin boshqaruvi:", reply_markup=InlineKeyboardMarkup(kb))

# Tovar qo'shish jarayoni
async def add_start(update, context):
    query = update.callback_query
    await query.answer()
    conn = sqlite3.connect('items.db')
    cats = conn.execute("SELECT DISTINCT category FROM items").fetchall()
    conn.close()
    kb = [[InlineKeyboardButton(c[0], callback_data=f"selcat_{c[0]}")] for c in cats]
    kb.append([InlineKeyboardButton("➕ Yangi guruh", callback_data="new_cat")])
    await query.message.edit_text("Guruhni tanlang yoki yangisini yarating:", reply_markup=InlineKeyboardMarkup(kb))
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

# Savat va o'chirish
async def show_cart(update, context):
    conn = sqlite3.connect('items.db')
    cart = conn.execute("SELECT i.name, c.quantity FROM cart c JOIN items i ON c.item_id = i.rowid WHERE c.user_id = ?", (update.effective_user.id,)).fetchall()
    conn.close()
    text = "🛒 Savatingiz:\n" + "\n".join([f"{i[0]} - {i[1]}" for i in cart]) if cart else "Savat bo'sh."
    await update.message.reply_text(text)

async def del_item_menu(update, context):
    query = update.callback_query
    await query.answer()
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

async def show_cat(update, context):
    cat = update.callback_query.data.split("_")[1]
    conn = sqlite3.connect('items.db')
    items = conn.execute("SELECT rowid, name FROM items WHERE category = ?", (cat,)).fetchall()
    conn.close()
    kb = [[InlineKeyboardButton(i[1], callback_data=f"show_{i[0]}")] for i in items]
    await update.callback_query.message.edit_text(f"📦 {cat} guruhi:", reply_markup=InlineKeyboardMarkup(kb))

async def show_item(update, context):
    item_id = update.callback_query.data.split("_")[1]
    context.user_data['item_id'] = item_id
    conn = sqlite3.connect('items.db')
    item = conn.execute("SELECT * FROM items WHERE rowid = ?", (item_id,)).fetchone()
    conn.close()
    await update.callback_query.message.reply_photo(item[2], caption=f"📦 {item[0]}\n💰 Narxi: {item[1]}\n📝 {item[3]}", 
                                                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🛒 Buyurtma berish", callback_data=f"order_{item_id}")]]))

async def order_start(update, context):
    context.user_data['item_id'] = update.callback_query.data.split("_")[1]
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
    
    add_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_start, pattern='add_item')],
        states={
            CATEGORY: [CallbackQueryHandler(select_cat, pattern='^selcat_|^new_cat$'), MessageHandler(filters.TEXT, get_cat_name)],
            NAME: [MessageHandler(filters.TEXT, get_name)],
            PRICE: [MessageHandler(filters.TEXT, get_price)],
            DESC: [MessageHandler(filters.TEXT, get_desc)],
            IMAGE: [MessageHandler(filters.PHOTO, get_image)]
        },
        fallbacks=[CommandHandler("start", start)])

    order_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(order_start, pattern=r'^order_\d+$')],
        states={QUANTITY: [MessageHandler(filters.TEXT, get_quantity)]},
        fallbacks=[CommandHandler("start", start)])

    app.add_handler(add_conv)
    app.add_handler(order_conv)
    app.add_handler(CallbackQueryHandler(del_item_menu, pattern='del_item'))
    app.add_handler(CallbackQueryHandler(perform_delete, pattern=r'^del_\d+$'))
    app.add_handler(CallbackQueryHandler(show_cat, pattern=r'^cat_'))
    app.add_handler(CallbackQueryHandler(show_item, pattern=r'^show_\d+$'))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT, handle_main))
    app.run_polling()
