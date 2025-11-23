import os
import logging
from dotenv import load_dotenv
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from src.bot import start_command, handle_message, error_handler, set_global_token # <--- NEU
from src.db import init_db

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if __name__ == '__main__':
    if not TOKEN:
        print("FEHLER: TELEGRAM_BOT_TOKEN fehlt!")
        exit(1)

    print("--- Initialisiere Datenbank ---")
    init_db()
    
    # WICHTIG: Token für proaktives Senden setzen
    set_global_token(TOKEN)

    print("--- Starte Bot ---")
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)
    
    print("Bot läuft! Drücke STRG+C zum Stoppen.")
    app.run_polling()