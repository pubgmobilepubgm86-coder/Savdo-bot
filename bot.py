import os
import time
import logging
import threading
import requests
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# Loglarni sozlash
logging.basicConfig(level=logging.INFO)

# 1. BOT TOKEN
BOT_TOKEN = "8845838662:AAFg9jJjjzvQlIASzEDQCLz9EcaZ3FDb6OU"

# 2. FLASK VEB-SERVER QISMI
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot muvaffaqiyatli 24/7 rejimda ishlamoqda!"

def run_flask():
    # Render beradigan portni oladi, bo'lmasa 8080
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# 3. SELF-PING (BOTNI UYG'OQ SAQLASH)
def self_ping():
    # 20 soniya kutib keyin ping boshlaydi
    time.sleep(20)
    url = os.environ.get("RENDER_EXTERNAL_URL")
    if not url:
        logging.warning("RENDER_EXTERNAL_URL topilmadi. Self-ping ishga tushmadi.")
        return
        
    while True:
        try:
            response = requests.get(url)
            logging.info(f"Self-ping bajarildi. Status kod: {response.status_code}")
        except Exception as e:
            logging.error(f"Self-pingda xatolik: {e}")
        time.sleep(600) # Har 10 daqiqada (600 soniya) bir marta

# 4. TELEGRAM BOT KOMANDALARI
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Salom! Men Render platformasida 24/7 ishlovchi botman.\n\n"
        "🔍 Menga 1xBet ID raqamini yuboring, men uning formatini tekshirib beraman!"
    )

async def check_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text
    
    # ID faqat raqam va uzunligi 8, 9 yoki 10 xonali bo'lishini tekshiramiz
    if user_input.isdigit() and 8 <= len(user_input) <= 10:
        await update.message.reply_text(f"✅ **ID formati to'g'ri:** `{user_input}`", parse_mode="Markdown")
    else:
        await update.message.reply_text("❌ **Noto'g'ri format!**\n1xBet ID faqat 8, 9 yoki 10 xonali raqamlardan iborat bo'lishi kerak.")

# MAIN (ISHGA TUSHIRISH)
def main():
    # Flask serverni alohida oqimda (thread) boshlash
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    # Self-pingni alohida oqimda boshlash
    ping_thread = threading.Thread(target=self_ping)
    ping_thread.daemon = True
    ping_thread.start()

    # Botni qurish va ishga tushirish
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_id))

    logging.info("Bot polling rejimida ishga tushdi...")
    application.run_polling()

if __name__ == '__main__':
    main()
    
