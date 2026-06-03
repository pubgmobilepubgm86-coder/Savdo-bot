import os
import time
import logging
import threading
import asyncio
import requests
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# Loglarni sozlash
logging.basicConfig(level=logging.INFO)

# --- MAXFIY SOZLAMALAR ---
BOT_TOKEN = "8845838662:AAFg9jJjjzvQlIASzEDQCLz9EcaZ3FDb6OU"
ADMIN_ID = 8086545587

# Ma'lumotlarni saqlovchi lug'atlar (Baza)
user_limits = {}  # Foydalanuvchilar qancha ID yuborganini saqlaydi
admin_states = {} # Admin qaysi foydalanuvchiga javob yozayotganini saqlaydi
bot_stats = {
    "total_users": set(), # Barcha start bosganlar
    "total_ids": 0        # Tekshirilgan jami ID lar soni
}

# --- FLASK VEB-SERVER (RENDER UCHUN) ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Signal bot 24/7 rejimda muammosiz ishlamoqda!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# --- SELF-PING (BOT UYQUGA KETMASLIGI UCHUN) ---
def self_ping():
    time.sleep(20)
    url = os.environ.get("RENDER_EXTERNAL_URL")
    if not url:
        return
    while True:
        try:
            requests.get(url)
        except Exception:
            pass
        time.sleep(600)

# --- TELEGRAM BOT BUYRUQLARI ---

# 1. /start buyrug'i
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    bot_stats["total_users"].add(user_id) # Foydalanuvchini bazaga qo'shamiz
    
    await update.message.reply_text(
        "👋 Salom! **Signal beruvchi botga** xush kelibsiz.\n\n"
        "🎰 Signal olish uchun 1xBet ID raqamingizni yuboring:"
    )

# 2. /admin buyrug'i (Faqat adminga ko'rinadi)
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id != ADMIN_ID:
        return # Agar boshqa odam /admin yozsa, bot hech narsa demaydi

    keyboard = [
        [InlineKeyboardButton("🔄 Yangilash", callback_data="admin_refresh")],
        [InlineKeyboardButton("🗑 Barcha limitlarni tozalash", callback_data="admin_reset")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = (
        "⚙️ **Admin Panel**\n\n"
        f"👥 Jami foydalanuvchilar: {len(bot_stats['total_users'])}\n"
        f"🔢 Kiritilgan ID lar soni: {bot_stats['total_ids']}"
    )
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

# 3. Foydalanuvchilar kiritgan matnlarni qabul qilish
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_text = update.message.text
    bot_stats["total_users"].add(user_id)

    # A) Agar Admin kimgadir javob yozyotgan bo'lsa
    if user_id == ADMIN_ID and user_id in admin_states:
        state = admin_states[user_id]
        if state.get("action") == "waiting_for_reply":
            target_user = state.get("target_user_id")
            try:
                await context.bot.send_message(
                    chat_id=target_user,
                    text=f"✉️ **Admin javobi:**\n\n{user_text}",
                    parse_mode="Markdown"
                )
                await update.message.reply_text("✅ Xabar foydalanuvchiga muvaffaqiyatli yetkazildi!")
            except Exception as e:
                await update.message.reply_text(f"❌ Xabar yuborishda xatolik (Foydalanuvchi botni bloklagan bo'lishi mumkin): {e}")
            
            del admin_states[user_id] # Admin holatini tozalash
            return

    # B) Foydalanuvchi ID kiritganda
    if user_text.isdigit() and 8 <= len(user_text) <= 10:
        # Limitni tekshirish
        current_count = user_limits.get(user_id, 0)
        if current_count >= 2:
            await update.message.reply_text("❌ **Xatolik:** Siz 2 tadan ko'p ID kiritgansiz! Boshqa ID tekshirish taqiqlanadi.")
            return

        # Limitni oshirish
        user_limits[user_id] = current_count + 1
        bot_stats["total_ids"] += 1

        # Foydalanuvchiga tasdiq
        await update.message.reply_text("📥 **ID ingiz tekshiruvga yuborildi, tez orada xabar keladi.**")

        # Adminga xabar yuborish paneli
        keyboard = [
            [InlineKeyboardButton("✍️ Javob berish", callback_data=f"reply_{user_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        username = f"@{update.message.from_user.username}" if update.message.from_user.username else "Mavjud emas"
        admin_msg = (
            f"🔔 **Yangi ID tekshiruvda!**\n\n"
            f"👤 Ism: {update.message.from_user.full_name}\n"
            f"🆔 Telegram ID: `{user_id}`\n"
            f"🌐 Username: {username}\n"
            f"🎰 **Kiritilgan ID:** `{user_text}`\n"
            f"📊 Limit holati: {user_limits[user_id]}/2"
        )
        
        # Adminga xabar yuborishga harakat qilish
        try:
            await context.bot.send_message(chat_id=ADMIN_ID, text=admin_msg, reply_markup=reply_markup, parse_mode="Markdown")
        except Exception as e:
            logging.error(f"Adminga xabar yuborib bo'lmadi: {e}")

    else:
        await update.message.reply_text("❌ **Noto'g'ri format!**\n1xBet ID faqat 8, 9 yoki 10 xonali raqamlardan iborat bo'lishi kerak.")

# 4. Inline tugmalar (Javob berish, Yangilash, Tozalash) bosilganda
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    # Faqat admin ishlata oladigan tugmalar
    if user_id != ADMIN_ID:
        return

    data = query.data

    if data.startswith("reply_"):
        target_user_id = int(data.split("_")[1])
        admin_states[ADMIN_ID] = {
            "action": "waiting_for_reply",
            "target_user_id": target_user_id
        }
        await query.message.reply_text(f"💬 `{target_user_id}` foydalanuvchisiga javob matnini yozing:")

    elif data == "admin_refresh":
        text = (
            "⚙️ **Admin Panel**\n\n"
            f"👥 Jami foydalanuvchilar: {len(bot_stats['total_users'])}\n"
            f"🔢 Kiritilgan ID lar soni: {bot_stats['total_ids']}"
        )
        await query.edit_message_text(text, reply_markup=query.message.reply_markup, parse_mode="Markdown")

    elif data == "admin_reset":
        user_limits.clear() # Barcha limitlarni 0 ga tushiradi
        await query.message.reply_text("✅ Barcha foydalanuvchilar uchun 2 talik ID limiti nolga tushirildi!")

# --- ASOSIY YUKLASH TIZIMI ---
async def main():
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    ping_thread = threading.Thread(target=self_ping)
    ping_thread.daemon = True
    ping_thread.start()

    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("admin", admin_panel)) # Admin komandasi
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logging.info("Mukammal Signal bot ishga tushdi...")
    
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    
    while True:
        await asyncio.sleep(3600)

if __name__ == '__main__':
    asyncio.run(main())
    
