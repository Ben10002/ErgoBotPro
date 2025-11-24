import os
import logging
from dotenv import load_dotenv
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from src.bot import start_command, handle_message, error_handler, set_global_token
from src.db import init_db

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if __name__ == '__main__':
    if not TOKEN:
        print("FEHLER: TELEGRAM_BOT_TOKEN fehlt in .env!")
        exit(1)

    print("=" * 50)
    print("🤖 ErgoBotPro - Intelligenter Telegram Agent")
    print("=" * 50)
    
    print("\n📊 Initialisiere Datenbank...")
    init_db()
    print("✅ Datenbank bereit\n")
    
    # Token für proaktives Senden setzen
    set_global_token(TOKEN)
    
    print("🚀 Starte Bot...")
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)
    
    print("✅ Bot läuft!")
    print("💡 Web-Dashboard: http://127.0.0.1:5000")
    print("⚠️  Drücke STRG+C zum Stoppen\n")
    print("=" * 50)
    
    app.run_polling()