import os
import logging
import threading
import requests
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# Sozlamalar
BOT_TOKEN = "8845838662:AAFg9jJjjzvQlIASzEDQCLz9EcaZ3FDb6OU"
ADMIN_ID = 8086545587

# Ma'lumotlar bazasi (xotirada)
user_limits = {} 
reply_state = {} 
bot_stats = {"users": set(), "ids_count": 0}

logging.basicConfig(level=logging.INFO)

# Flask Server (Render 24/7 ishlashi uchun)
app = Flask(__name__)
@app.route('/')
def home(): return "Bot ishlamoqda!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# Self-ping (bot uxlab qolmasligi uchun)
def self_ping():
    url = os.environ.get("RENDER_EXTERNAL_URL")
    if url:
        while True:
            try: requests.get(url)
            except: pass
            import time; time.sleep(600)

# Bot Logic
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    bot_stats["users"].add(user.id)
    await update.message.reply_text("👋 Salom! Signal olish uchun 1xBet ID raqamingizni yuboring.")

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID: return
    keyboard = [[InlineKeyboardButton("🗑 Limitlarni tozalash", callback_data="reset_limits")]]
    await update.message.reply_text(
        f"⚙️ **Admin Panel**\n👥 Foydalanuvchilar: {len(bot_stats['users'])}\n🔢 Jami ID: {bot_stats['ids_count']}",
        reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    text = update.message.text
    
    # Admin javob yozayotgan bo'lsa
    if user.id == ADMIN_ID and user.id in reply_state:
        target_id = reply_state.pop(user.id)
        await context.bot.send_message(chat_id=target_id, text=f"📩 **Admin javobi:**\n\n{text}", parse_mode="Markdown")
        await update.message.reply_text("✅ Xabar yuborildi.")
        return

    # Foydalanuvchi ID yuborganda
    if text.isdigit() and 8 <= len(text) <= 10:
        if user_limits.get(user.id, 0) >= 2:
            await update.message.reply_text("❌ Siz allaqachon 2 ta ID yuborgansiz.")
            return
        
        user_limits[user.id] = user_limits.get(user.id, 0) + 1
        bot_stats["ids_count"] += 1
        
        keyboard = [[InlineKeyboardButton("✍️ Javob berish", callback_data=f"reply_{user.id}")]]
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"🔔 **Yangi ID:** `{text}`\n👤 **User:** {user.full_name}\n🆔 `{user.id}`",
            reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
        )
        await update.message.reply_text("📥 ID qabul qilindi, adminga yuborildi.")
    else:
        await update.message.reply_text("❌ Noto'g'ri format! 8-10 xonali son kiriting.")

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data.startswith("reply_"):
        reply_state[ADMIN_ID] = int(query.data.split("_")[1])
        await query.message.reply_text("💬 Javob matnini yozing:")
    elif query.data == "reset_limits":
        user_limits.clear()
        await query.message.reply_text("✅ Limitlar tozalandi.")

if __name__ == '__main__':
    threading.Thread(target=run_flask, daemon=True).start()
    threading.Thread(target=self_ping, daemon=True).start()
    
    app_bot = ApplicationBuilder().token(BOT_TOKEN).build()
    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(CommandHandler("admin", admin_panel))
    app_bot.add_handler(CallbackQueryHandler(button_click))
    app_bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    app_bot.run_polling()
    
