import asyncio
import random
import re
import json
from datetime import datetime, timedelta
from telegram import Update, constants, Bot
from telegram.ext import ContextTypes
from src.ai import (
    get_chatgpt_response, 
    extract_facts_from_text, 
    get_proactive_message, 
    generate_sales_move
)
from src.db import (
    add_user, save_message, get_chat_history, is_user_active, 
    add_fact, get_fact_value, is_human_mode_on, get_user, get_user_facts,
    add_contact, add_lead_signal
)

# Globale Variablen
GLOBAL_BOT_TOKEN = None
TIME_OFFSET = 1  # Zeitverschiebung (falls nötig)

def set_global_token(token):
    """Setzt das Bot-Token für proaktive Nachrichten"""
    global GLOBAL_BOT_TOKEN
    GLOBAL_BOT_TOKEN = token

def get_current_time():
    """Gibt die aktuelle Zeit mit Offset zurück"""
    return datetime.now() + timedelta(hours=TIME_OFFSET)

def is_in_quiet_hours(user_id, q_start, q_end):
    """
    Prüft ob User in Nachtruhe ist.
    Fügt zufällige Varianz hinzu für natürlicheres Verhalten.
    """
    now = get_current_time()
    current_minutes = now.hour * 60 + now.minute
    
    # Tägliche Zufallsvariation (konsistent pro Tag)
    seed_val = now.toordinal() + user_id
    random.seed(seed_val)
    offset_start = random.randint(-15, 15)
    offset_end = random.randint(-15, 15)
    
    start_m = (q_start * 60 + offset_start) % 1440
    end_m = (q_end * 60 + offset_end) % 1440
    
    # Über Mitternacht hinweg
    if start_m > end_m:
        if current_minutes >= start_m or current_minutes < end_m:
            return True, offset_start, offset_end
    else:
        if start_m <= current_minutes < end_m:
            return True, offset_start, offset_end
    
    return False, offset_start, offset_end

def calculate_lead_score(facts_dict):
    """
    Intelligenter Lead-Score Algorithmus.
    Bewertet User auf Skala 0-10 für Altersvorsorge-Eignung.
    """
    score = 0
    max_score = 10
    
    facts = facts_dict.get('facts', {})
    meta = facts_dict.get('meta', {})
    
    # Lead Signals aus DB holen (wenn als JSON gespeichert)
    signals = []
    if 'signals' in facts_dict and 'lead_signals' in facts_dict['signals']:
        try:
            signals = json.loads(facts_dict['signals']['lead_signals'])
            if not isinstance(signals, list):
                signals = []
        except:
            signals = []
    
    # Kontakte aus DB
    contacts = []
    if 'contacts' in facts_dict and 'kontakte' in facts_dict['contacts']:
        try:
            contacts = json.loads(facts_dict['contacts']['kontakte'])
            if not isinstance(contacts, list):
                contacts = []
        except:
            contacts = []
    
    # === DEMOGRAFISCHE BASIS (max 2 Punkte) ===
    if 'alter' in facts:
        try:
            age_str = str(facts['alter'])
            age_match = re.findall(r'\d+', age_str)
            if age_match:
                age = int(age_match[0])
                if 25 <= age <= 45:
                    score += 1.5  # Prime Zielgruppe
                elif 18 <= age <= 55:
                    score += 0.5
        except:
            pass
    
    if 'beruf' in facts:
        beruf = str(facts['beruf']).lower()
        if beruf not in ['arbeitslos', 'student', 'schüler', 'rentner']:
            score += 0.5
    
    # === FINANZIELLE INDIKATOREN (max 3 Punkte) ===
    facts_lower = str(facts).lower()
    
    # Direktes Einkommen
    income_keys = ['einkommen', 'gehalt', 'verdienst', 'netto', 'brutto', 'lohn']
    if any(k in facts_lower for k in income_keys):
        score += 1.5
    
    # Indirekte Kaufkraft
    wealth_signals = [
        'eigentum', 'wohnung gekauft', 'haus', 'eigenheim',
        'bmw', 'audi', 'mercedes', 'porsche',
        'luxus', 'urlaub', 'reise', 'fernreise'
    ]
    wealth_count = sum(1 for sig in wealth_signals if sig in facts_lower)
    score += min(1, wealth_count * 0.3)
    
    # Sparverhalten
    if any(k in facts_lower for k in ['spar', 'rücklage', 'investment', 'anlage']):
        score += 0.5
    
    # === PSYCHOLOGISCHE FAKTOREN (max 2 Punkte) ===
    meta_lower = str(meta).lower()
    
    if meta:
        # Zukunftsorientierung
        if any(w in meta_lower for w in ['zukunft', 'plant', 'überlegt', 'vorausschau']):
            score += 0.7
        
        # Finanzielle Unsicherheit (Chance!)
        if any(w in meta_lower for w in ['unsicher', 'keine ahnung', 'stress', 'sorge', 'angst']):
            score += 0.8
        
        # Offenheit
        if any(w in meta_lower for w in ['offen', 'teilt', 'vertrauensvoll']):
            score += 0.5
    
    # === LEAD SIGNALS (max 2 Punkte) ===
    score += min(2, len(signals) * 0.4)
    
    # === NETZWERK-POTENZIAL (max 1 Punkt) ===
    if contacts:
        high_potential = sum(1 for c in contacts 
                           if isinstance(c, dict) and 
                           c.get('potential', '').lower() in ['hoch', 'mittel', 'high', 'medium'])
        score += min(1, high_potential * 0.5)
    
    # Auf 10 normalisieren
    final_score = min(max_score, round(score, 1))
    
    return int(final_score)

async def trigger_ai_message(user_id):
    """
    Löst eine proaktive KI-Nachricht aus.
    Wird vom Dashboard über den ✨-Button aufgerufen.
    """
    if not GLOBAL_BOT_TOKEN:
        print("❌ Kein Bot-Token gesetzt!")
        return False
    
    try:
        history = get_chat_history(user_id, limit=20)
        clean = [{"role": m["role"], "content": m["content"]} for m in history]
        
        ai_text = await get_proactive_message(clean)
        
        if ai_text:
            bot = Bot(token=GLOBAL_BOT_TOKEN)
            await bot.send_message(chat_id=user_id, text=ai_text)
            save_message(user_id, "assistant", ai_text)
            print(f"✅ Proaktive Nachricht an {user_id} gesendet")
            return True
    except Exception as e:
        print(f"❌ Fehler bei proaktiver Nachricht: {e}")
    
    return False

async def simulate_human_delay(user_id, context, chat_id, ai_response_text):
    """
    Simuliert menschliches Antwortverhalten mit:
    - Realistischen Verzögerungen
    - Typing-Anzeige
    - Kontextabhängigem Timing
    """
    if not is_human_mode_on(user_id):
        return
    
    now = get_current_time()
    history = get_chat_history(user_id, limit=2)
    
    # Prüfe ob Gespräch "im Flow" ist
    last_msg_time = None
    if len(history) >= 2:
        try:
            time_str = str(history[-2]['timestamp']).split('.')[0]
            last_msg_time = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
        except:
            last_msg_time = now
    
    in_flow = False
    if last_msg_time:
        time_diff = (datetime.now() - last_msg_time).total_seconds()
        if time_diff < 300:  # Letzte Nachricht < 5 Min
            in_flow = True
    
    # Delay berechnen
    if in_flow:
        delay_seconds = random.randint(3, 8)  # Schnelle Antwort
    else:
        delay_seconds = random.randint(15, 60)  # Gemütliche Antwort
    
    print(f"⏳ Warte {delay_seconds}s vor Antwort...")
    
    if delay_seconds > 0:
        await asyncio.sleep(delay_seconds)
    
    # Typing-Simulation
    typing_seconds = min(12, 1.5 + (len(ai_response_text) * 0.05))
    
    await context.bot.send_chat_action(
        chat_id=chat_id, 
        action=constants.ChatAction.TYPING
    )
    
    print(f"⌨️  Tippt {typing_seconds:.1f}s...")
    await asyncio.sleep(typing_seconds)

# ==================== TELEGRAM HANDLERS ====================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler für /start Command"""
    user = update.effective_user
    add_user(user.id, user.username, user.first_name)
    
    msg = "Hey! Ich bin Benni. Was geht?"
    save_message(user.id, "assistant", msg)
    
    await update.message.reply_text(msg)
    print(f"👤 Neuer User: {user.first_name} (@{user.username})")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Hauptlogik für Nachrichtenverarbeitung.
    3-Phasen-Architektur: Analyst → Stratege → Texter
    """
    user = update.effective_user
    user_text = update.message.text
    chat_id = update.effective_chat.id

    # User in DB speichern/aktualisieren
    add_user(user.id, user.username, user.first_name)
    save_message(user.id, "user", user_text)
    
    print(f"\n{'='*50}")
    print(f"📩 NEUE NACHRICHT von {user.first_name}")
    print(f"{'='*50}")
    print(f"User: {user_text}")
    
    # Prüfen ob Bot aktiv
    if not is_user_active(user.id):
        print("⏸️  Bot ist für diesen User deaktiviert")
        return

    # Nachtruhe prüfen
    if is_human_mode_on(user.id):
        db_user = get_user(user.id)
        is_sleeping, _, _ = is_in_quiet_hours(
            user.id, 
            db_user['quiet_start'], 
            db_user['quiet_end']
        )
        if is_sleeping:
            print("😴 Nachtruhe aktiv - keine Antwort")
            return

    # Chat-Historie laden
    history = get_chat_history(user.id, limit=50)
    clean_history = [{"role": m["role"], "content": m["content"]} for m in history]
    
    # ==================== PHASE 1: ANALYST ====================
    print("\n🔍 PHASE 1: Analysiere Nachricht...")
    
    try:
        analysis_result = await extract_facts_from_text(
            user_text, 
            conversation_context=clean_history
        )
        
        # Fakten speichern
        if analysis_result.get('facts'):
            for key, value in analysis_result['facts'].items():
                if value and str(value).lower() not in ['unbekannt', 'keine angabe', '']:
                    add_fact(user.id, key, value, fact_type="fact")
                    print(f"  ✓ Fakt gespeichert: {key} = {value}")
        
        # Meta-Infos speichern
        if analysis_result.get('meta'):
            for key, value in analysis_result['meta'].items():
                add_fact(user.id, key, value, fact_type="meta")
                print(f"  ✓ Meta gespeichert: {key} = {value}")
        
        # Kontakte speichern
        if analysis_result.get('contacts'):
            contacts_json = json.dumps(
                analysis_result['contacts'], 
                ensure_ascii=False
            )
            add_fact(user.id, 'kontakte', contacts_json, fact_type="contacts")
            
            # Auch in separate Tabelle
            for contact in analysis_result['contacts']:
                if isinstance(contact, dict):
                    add_contact(
                        user.id,
                        contact.get('name', ''),
                        contact.get('beziehung', ''),
                        contact.get('info', ''),
                        contact.get('potential', 'unbekannt')
                    )
            print(f"  ✓ {len(analysis_result['contacts'])} Kontakt(e) gespeichert")
        
        # Lead Signals speichern
        if analysis_result.get('lead_signals'):
            signals_json = json.dumps(
                analysis_result['lead_signals'], 
                ensure_ascii=False
            )
            add_fact(user.id, 'lead_signals', signals_json, fact_type="signals")
            
            # Auch einzeln speichern
            for signal in analysis_result['lead_signals']:
                add_lead_signal(user.id, signal)
            
            print(f"  ✓ {len(analysis_result['lead_signals'])} Lead Signal(s)")
            
    except Exception as e:
        print(f"❌ Analysis Error: {e}")
    
    # Alle gesammelten Fakten laden
    all_known_facts = get_user_facts(user.id)
    
    # Lead Score berechnen
    lead_score = calculate_lead_score(all_known_facts)
    add_fact(user.id, 'lead_score', str(lead_score), fact_type="score")
    print(f"\n📊 Lead Score: {lead_score}/10")
    
    # ==================== PHASE 2: STRATEGE ====================
    print("\n🎯 PHASE 2: Plane Gesprächsstrategie...")
    
    strategic_plan = await generate_sales_move(
        user_text=user_text,
        current_facts=all_known_facts,
        chat_history=clean_history
    )
    
    # ==================== PHASE 3: TEXTER ====================
    print("\n✍️  PHASE 3: Generiere Antwort...")
    
    # Prüfe ob Stratege 2 Nachrichten will
    num_messages = 1
    if "[2 NACHRICHTEN]" in strategic_plan or "NACHRICHT 2" in strategic_plan:
        num_messages = 2
        print("📤 Plane 2 Nachrichten...")
    
    # Erste Nachricht generieren
    ai_response_1 = await get_chatgpt_response(
        clean_history,
        user_meta=all_known_facts.get('meta', {}),
        strategic_instruction=strategic_plan
    )
    
    # Human Delay & Senden
    await simulate_human_delay(user.id, context, chat_id, ai_response_1)
    save_message(user.id, "assistant", ai_response_1)
    await update.message.reply_text(ai_response_1)
    
    # Zweite Nachricht (falls geplant)
    if num_messages == 2:
        print("📤 Sende 2. Nachricht...")
        
        # Kurze Pause (2-5 Sekunden)
        await asyncio.sleep(random.randint(2, 5))
        
        # Historie aktualisieren mit erster Nachricht
        clean_history.append({"role": "assistant", "content": ai_response_1})
        
        # Zweite Nachricht mit angepasster Instruktion
        follow_up_instruction = "Jetzt die zweite Nachricht senden. Halte dich an den Plan. Kurz und natürlich."
        
        ai_response_2 = await get_chatgpt_response(
            clean_history,
            user_meta=all_known_facts.get('meta', {}),
            strategic_instruction=follow_up_instruction
        )
        
        # Typing simulation
        await context.bot.send_chat_action(chat_id=chat_id, action=constants.ChatAction.TYPING)
        await asyncio.sleep(random.randint(2, 4))
        
        save_message(user.id, "assistant", ai_response_2)
        await update.message.reply_text(ai_response_2)
        
        print(f"✅ 2 Nachrichten gesendet")
    else:
        print(f"✅ Antwort gesendet")
    
    print("="*50 + "\n")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Globaler Error Handler"""
    print(f"❌ ERROR: {context.error}")
    if update and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "Ups, da ist was schiefgelaufen. Versuch's nochmal?"
            )
        except:
            pass