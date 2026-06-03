import os
import logging
import threading
import requests
import time
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# --- SOZLAMALAR ---
BOT_TOKEN = "8845838662:AAFg9jJjjzvQlIASzEDQCLz9EcaZ3FDb6OU"
ADMIN_ID = 8086545587

# --- BAZA (Xotirada) ---
admin_actions = {}  # Admin javob jarayoni
bot_stats = {"users": set(), "ids_count": 0} # Statistika

logging.basicConfig(level=logging.INFO)

# --- FLASK (24/7 UCHUN) ---
app = Flask(__name__)
@app.route('/')
def home(): return "Bot 24/7 rejimda ishlamoqda!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# --- SELF-PING (UYQUGA KETMASLIK) ---
def self_ping():
    url = os.environ.get("RENDER_EXTERNAL_URL")
    if url:
        while True:
            try: requests.get(url)
            except: pass
            time.sleep(600)

# --- TELEGRAM BOT LOGIKASI ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_stats["users"].add(update.message.from_user.id)
    await update.message.reply_text("👋 Salom! Signal olish uchun 1xBet ID raqamingizni yuboring.")

# ADMIN PANEL
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id == ADMIN_ID:
        await update.message.reply_text(
            f"⚙️ **Admin Panel**\n👥 Jami foydalanuvchilar: {len(bot_stats['users'])}\n🔢 Jami IDlar: {bot_stats['ids_count']}",
            parse_mode="Markdown"
        )

# XABARLARNI QABUL QILISH
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text
    
    # 1. ADMIN JAVOB BERAYOTGAN BO'LSA
    if user_id == ADMIN_ID and user_id in admin_actions:
        state = admin_actions.pop(user_id)
        try:
            if state["action"] == "accept_fio":
                await context.bot.send_message(chat_id=state["target_id"], text=f"✅ **ID qabul qilindi!**\n👤 **Akkaunt egasi (F.I.O):** {text}", parse_mode="Markdown")
            else:
                await context.bot.send_message(chat_id=state["target_id"], text=f"❌ **ID rad etildi!**\nℹ️ **Sabab:** {text}", parse_mode="Markdown")
            await update.message.reply_text("✅ Javob yuborildi.")
        except Exception as e:
            await update.message.reply_text(f"❌ Xatolik: {e}")
        return

    # 2. FOYDALANUVCHI ID YUBORGANDA
    if text.isdigit() and 8 <= len(text) <= 10:
        bot_stats["ids_count"] += 1
        keyboard = [
            [InlineKeyboardButton("✅ Qabul qilindi", callback_data=f"accept_{user_id}"),
             InlineKeyboardButton("❌ Qabul qilinmadi", callback_data=f"reject_{user_id}")]
        ]
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"🎰 **Yangi ID:** `{text}`\n👤 **User:** {update.message.from_user.full_name}\n🆔 `{user_id}`",
            reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
        )
        await update.message.reply_text("📥 ID tekshiruvga yuborildi.")
    else:
        await update.message.reply_text("❌ Noto'g'ri format! 8-10 xonali son kiriting.")

# TUGMALARNI BOSISH
async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data.startswith("accept_"):
        admin_actions[ADMIN_ID] = {"action": "accept_fio", "target_id": int(data.split("_")[1])}
        await query.message.reply_text("📝 **F.I.O ni yozing:**")
    elif data.startswith("reject_"):
        admin_actions[ADMIN_ID] = {"action": "reject_reason", "target_id": int(data.split("_")[1])}
        await query.message.reply_text("📝 **Rad etish sababini yozing:**")

if __name__ == '__main__':
    threading.Thread(target=run_flask, daemon=True).start()
    threading.Thread(target=self_ping, daemon=True).start()
    
    app_bot = ApplicationBuilder().token(BOT_TOKEN).build()
    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(CommandHandler("admin", admin_panel))
    app_bot.add_handler(CallbackQueryHandler(button_click))
    app_bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    app_bot.run_polling()
    
