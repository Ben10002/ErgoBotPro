import asyncio
import random
from datetime import datetime, timedelta
from telegram import Update, constants, Bot
from telegram.ext import ContextTypes
from src.ai import get_chatgpt_response, extract_facts_from_text, get_proactive_message, generate_sales_move
from src.db import (
    add_user, save_message, get_chat_history, is_user_active, 
    add_fact, get_fact_value, is_human_mode_on, get_user, get_user_facts
)

SINGLE_VALUE_KEYS = ["name", "vorname", "alter", "geburtstag", "wohnort", "stadt", "adresse", "beziehungsstatus", "email"]
GLOBAL_BOT_TOKEN = None
TIME_OFFSET = 1 

def set_global_token(token):
    global GLOBAL_BOT_TOKEN
    GLOBAL_BOT_TOKEN = token

def get_current_time():
    return datetime.now() + timedelta(hours=TIME_OFFSET)

def is_in_quiet_hours(user_id, q_start, q_end):
    now = get_current_time()
    current_minutes = now.hour * 60 + now.minute
    seed_val = now.toordinal() + user_id
    random.seed(seed_val)
    offset_start = random.randint(-15, 15)
    offset_end = random.randint(-15, 15)
    start_m = (q_start * 60 + offset_start) % 1440
    end_m = (q_end * 60 + offset_end) % 1440
    if start_m > end_m:
        if current_minutes >= start_m or current_minutes < end_m: return True, offset_start, offset_end
    else:
        if start_m <= current_minutes < end_m: return True, offset_start, offset_end
    return False, offset_start, offset_end

async def trigger_ai_message(user_id):
    if not GLOBAL_BOT_TOKEN: return False
    try:
        history = get_chat_history(user_id, limit=20)
        clean = [{"role": m["role"], "content": m["content"]} for m in history]
        ai_text = await get_proactive_message(clean)
        if ai_text:
            bot = Bot(token=GLOBAL_BOT_TOKEN)
            await bot.send_message(chat_id=user_id, text=ai_text)
            save_message(user_id, "assistant", ai_text)
            return True
    except Exception as e: print(f"Fehler: {e}")
    return False

async def simulate_human_delay(user_id, context, chat_id, ai_response_text):
    if not is_human_mode_on(user_id): return 
    now = get_current_time()
    history = get_chat_history(user_id, limit=2)
    last_msg_time = None
    if len(history) >= 2:
        try: last_msg_time = datetime.strptime(str(history[-2]['timestamp']).split('.')[0], "%Y-%m-%d %H:%M:%S")
        except: last_msg_time = now 
    in_flow = False
    if last_msg_time:
        if (datetime.now() - last_msg_time).total_seconds() < 300: in_flow = True
    
    delay_seconds = random.randint(3, 8) if in_flow else random.randint(15, 60)
    if delay_seconds > 0: await asyncio.sleep(delay_seconds)
    
    typing_seconds = min(12, 1.5 + (len(ai_response_text) * 0.05))
    await context.bot.send_chat_action(chat_id=chat_id, action=constants.ChatAction.TYPING)
    await asyncio.sleep(typing_seconds)

# --- HANDLER ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_user(user.id, user.username, user.first_name)
    msg = "Hey! Ich bin Benni."
    save_message(user.id, "assistant", msg)
    await update.message.reply_text(msg)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_text = update.message.text
    chat_id = update.effective_chat.id

    add_user(user.id, user.username, user.first_name)
    save_message(user.id, "user", user_text)

    if not is_user_active(user.id): return

    if is_human_mode_on(user.id):
        db_user = get_user(user.id)
        is_sleeping, _, _ = is_in_quiet_hours(user.id, db_user['quiet_start'], db_user['quiet_end'])
        if is_sleeping: return 

    # --- PHASE 1: ANALYST ---
    try:
        result = await extract_facts_from_text(user_text)
        if 'facts' in result:
            for key, new_val in result['facts'].items():
                if not new_val or new_val == "unbekannt": continue
                old_val = get_fact_value(user.id, key)
                if old_val and key.lower() not in SINGLE_VALUE_KEYS:
                    if new_val not in old_val: final_val = f"{old_val}, {new_val}"
                    else: final_val = old_val
                else: final_val = new_val
                add_fact(user.id, key, final_val, fact_type="fact")
        if 'meta' in result:
            for key, new_val in result['meta'].items():
                add_fact(user.id, key, new_val, fact_type="meta")
    except: pass
    
    all_known_facts = get_user_facts(user.id) 

    # --- WICHTIG: Verlauf laden BEVOR der Stratege plant ---
    history = get_chat_history(user.id, limit=50)
    clean_history = [{"role": m["role"], "content": m["content"]} for m in history]

    # --- PHASE 2: STRATEGE (PLANEN) ---
    strategic_plan = await generate_sales_move(
        user_text=user_text, 
        current_facts=all_known_facts,
        chat_history=clean_history # <--- NEU: Übergabe des Verlaufs
    )
    print(f"DEBUG STRATEGIE: {strategic_plan}")

    # --- PHASE 3: TEXTER (AUSFÜHREN) ---
    ai_response = await get_chatgpt_response(
        clean_history, 
        user_meta=all_known_facts.get('meta', {}), 
        strategic_instruction=strategic_plan
    )
    
    await simulate_human_delay(user.id, context, chat_id, ai_response)
    save_message(user.id, "assistant", ai_response)
    await update.message.reply_text(ai_response)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"Fehler: {context.error}")