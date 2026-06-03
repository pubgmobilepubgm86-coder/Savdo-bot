import os
import logging
import threading
import time
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# --- SOZLAMALAR ---
BOT_TOKEN = "8845838662:AAGzJqrJU1COnVKChdpwxnCHQoRlI4xZKgw"
ADMIN_ID = 8086545587

# --- BAZA (Xotirada) ---
admin_actions = {}
bot_stats = {"users": set(), "ids_count": 0}

logging.basicConfig(level=logging.INFO)

# --- FLASK (Render 24/7 ishlashi uchun) ---
app = Flask(__name__)
@app.route('/')
def home(): return "Bot ishlamoqda!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# --- SELF-PING ---
def self_ping():
    import requests
    url = os.environ.get("RENDER_EXTERNAL_URL")
    if url:
        while True:
            try: requests.get(url)
            except: pass
            time.sleep(600)

# --- BOT LOGIKASI ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_stats["users"].add(update.message.from_user.id)
    await update.message.reply_text("👋 Salom! Signal olish uchun 1xBet ID raqamingizni yuboring.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text
    
    # ADMIN JAVOB JARAYONI
    if user_id == ADMIN_ID and user_id in admin_actions:
        state = admin_actions.pop(user_id)
        try:
            if state["action"] == "accept":
                await context.bot.send_message(chat_id=state["target_id"], text=f"✅ **ID qabul qilindi!**\n👤 **Akkaunt egasi (F.I.O):** {text}", parse_mode="Markdown")
            else:
                await context.bot.send_message(chat_id=state["target_id"], text=f"❌ **ID rad etildi!**\nℹ️ **Sabab:** {text}", parse_mode="Markdown")
            await update.message.reply_text("✅ Javob yuborildi.")
        except:
            await update.message.reply_text("❌ Xatolik! Foydalanuvchi botni bloklagan bo'lishi mumkin.")
        return

    # FOYDALANUVCHI ID YUBORGANDA
    if text.isdigit() and 8 <= len(text) <= 10:
        bot_stats["ids_count"] += 1
        keyboard = [
            [InlineKeyboardButton("✅ Qabul qilindi", callback_data=f"accept_{user_id}")],
            [InlineKeyboardButton("❌ Qabul qilinmadi", callback_data=f"reject_{user_id}")]
        ]
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"🎰 **Yangi ID:** `{text}`\n👤 **User:** {update.message.from_user.full_name}\n🆔 `{user_id}`",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        await update.message.reply_text("📥 ID tekshiruvga yuborildi.")
    else:
        await update.message.reply_text("❌ Noto'g'ri format! 8-10 xonali son kiriting.")

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data.startswith("accept_"):
        admin_actions[ADMIN_ID] = {"action": "accept", "target_id": int(data.split("_")[1])}
        await query.edit_message_text(f"{query.message.text}\n\n✅ Qabul qilindi, F.I.O yozing:", parse_mode="Markdown")
    elif data.startswith("reject_"):
        admin_actions[ADMIN_ID] = {"action": "reject", "target_id": int(data.split("_")[1])}
        await query.edit_message_text(f"{query.message.text}\n\n❌ Rad etildi, sababni yozing:", parse_mode="Markdown")

if __name__ == '__main__':
    threading.Thread(target=run_flask, daemon=True).start()
    threading.Thread(target=self_ping, daemon=True).start()
    
    app_bot = ApplicationBuilder().token(BOT_TOKEN).build()
    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(CallbackQueryHandler(button_click))
    app_bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    app_bot.run_polling()
        
