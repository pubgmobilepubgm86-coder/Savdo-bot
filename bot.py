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

# --- SOZLAMALAR ---
BOT_TOKEN = "8845838662:AAFg9jJjjzvQlIASzEDQCLz9EcaZ3FDb6OU"
ADMIN_ID = 8086545587

# Ma'lumotlarni vaqtincha saqlash (Bot o'chib yonsa tozalanadi)
user_limits = {}  # {user_id: kiritilgan_idlar_soni}
admin_states = {} # {admin_id: {"action": "reply", "target_user_id": 12345}}

# --- FLASK VEB-SERVER (RENDER UCHUN) ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Signal beruvchi bot 24/7 rejimda ishlamoqda!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# --- SELF-PING (UYQUGA KETMASLIK) ---
def self_ping():
    time.sleep(20)
    url = os.environ.get("RENDER_EXTERNAL_URL")
    if not url:
        logging.warning("RENDER_EXTERNAL_URL topilmadi. Self-ping ishga tushmadi.")
        return
    while True:
        try:
            response = requests.get(url)
            logging.info(f"Self-ping bajarildi. Status: {response.status_code}")
        except Exception as e:
            logging.error(f"Self-pingda xatolik: {e}")
        time.sleep(600)

# --- TELEGRAM BOT LOGIKASI ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Salom! **Signal beruvchi botga** xush kelibsiz.\n\n"
        "Matndagi xatoliklarni to'g'rilash va signal olish uchun 1xBet ID raqamingizni yuboring:"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_text = update.message.text

    # --- ADMIN JAVOB BERISH REJIMIDA BO'LSA ---
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
                await update.message.reply_text("✅ Xabaringiz foydalanuvchiga muvaffaqiyatli yetkazildi!")
            except Exception as e:
                await update.message.reply_text(f"❌ Xabar yuborishda xatolik (Foydalanuvchi botni bloklagan bo'lishi mumkin): {e}")
            
            # Admin holatini tozalaymiz
            del admin_states[user_id]
            return

    # --- FOYDALANUVCHIDAN ID QABUL QILISH ---
    if user_text.isdigit() and 8 <= len(user_text) <= 10:
        # Limitni tekshirish (ko'pi bilan 2 ta ID)
        current_count = user_limits.get(user_id, 0)
        if current_count >= 2:
            await update.message.reply_text("❌ **Xatolik:** Siz 2 tadan ko'p ID kiritgansiz! Boshqa ID tekshirish taqiqlanadi.")
            return

        # Limitni oshiramiz
        user_limits[user_id] = current_count + 1

        # Foydalanuvchiga tasdiq xabari
        await update.message.reply_text("📥 **ID ingiz tekshiruvga yuborildi, tez orada xabar keladi.**")

        # Adminga inline tugma bilan xabar yuborish
        keyboard = [
            [InlineKeyboardButton("✍️ Javob berish matni", callback_data=f"reply_{user_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        username = f"@{update.message.from_user.username}" if update.message.from_user.username else "Mavjud emas"
        admin_msg = (
            f"🔔 **Yangi ID keldi!**\n\n"
            f"👤 **Foydalanuvchi:** {update.message.from_user.full_name}\n"
            f"🆔 **Telegram ID:** `{user_id}`\n"
            f"🌐 **Username:** {username}\n"
            f"🎰 **Kiritilgan 1xBet ID:** `{user_text}`\n"
            f"📊 **Urinishlar soni:** {user_limits[user_id]}/2"
        )
        
        await context.bot.send_message(chat_id=ADMIN_ID, text=admin_msg, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await update.message.reply_text("❌ **Noto'g'ri format!**\n1xBet ID faqat 8, 9 yoki 10 xonali raqamlardan iborat bo'lishi kerak.")

# --- INLINE TUGMA BOSILGANDA ---
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data.startswith("reply_"):
        target_user_id = int(query.data.split("_")[1])
        
        # Admin holatini o'zgartiramiz, bot navbatdagi matnni javob deb qabul qiladi
        admin_states[ADMIN_ID] = {
            "action": "waiting_for_reply",
            "target_user_id": target_user_id
        }
        
        await query.message.reply_text(
            f"💬 `🆔 {target_user_id}` foydalanuvchisiga yubormoqchi bo'lgan javob matningizni yozing:\n"
            f"(Yuborgan keyingi matnli xabaringiz unga boradi)"
        )

# --- MAIN ISHGA TUSHIRISH ---
async def main():
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    ping_thread = threading.Thread(target=self_ping)
    ping_thread.daemon = True
    ping_thread.start()

    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logging.info("Signal bot polling rejimida ishga tushdi...")
    
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    
    while True:
        await asyncio.sleep(3600)

if __name__ == '__main__':
    asyncio.run(main())
    
