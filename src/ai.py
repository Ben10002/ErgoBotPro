import os
import json
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()
client = AsyncOpenAI()

# --- 3. DER TEXTER (ACTOR) ---
async def get_chatgpt_response(history_messages, user_meta=None, strategic_instruction=None):
    try:
        system_prompt = (
            "Du bist Benni. Ein normaler Typ (28, WG, Job im Büro). KEINE KI.\n"
            "Stil: Locker, authentisch, manchmal schreibfaul (nutze 'nen', 'mal', 'echt', 'safe').\n"
            "WICHTIG: Halte dich strikt an die Regieanweisung.\n"
        )
        
        if user_meta:
            system_prompt += f"\nInfo zum User: Stil='{user_meta.get('Kommunikationsstil', 'normal')}'."

        if strategic_instruction:
            system_prompt += f"\n!!! REGIEANWEISUNG (STRATEGIE) !!!\n{strategic_instruction}\n"
            if "KEINE FRAGE" in strategic_instruction.upper():
                system_prompt += "VERBOT: Beende den Satz mit einem Punkt. Keine Gegenfrage!\n"
            if "KURZ" in strategic_instruction.upper():
                system_prompt += "LÄNGE: Maximal 1-2 kurze Sätze. Kein Gelaber.\n"

        full_conversation = [{"role": "system", "content": system_prompt}] + history_messages
        
        response = await client.chat.completions.create(
            model="gpt-4o", 
            messages=full_conversation,
            max_tokens=200,
            temperature=0.85
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Texter Error: {e}")
        return "..."

# --- 2. DER STRATEGE (PLANNER) - JETZT MIT KONTEXT-GEDÄCHTNIS ---
async def generate_sales_move(user_text, current_facts, chat_history):
    try:
        msg_count = len(chat_history)
        # Letzte eigene Nachricht analysieren (um Themen-Hopping zu vermeiden)
        last_bot_msg = ""
        if msg_count > 1 and chat_history[-2]['role'] == 'assistant':
            last_bot_msg = chat_history[-2]['content']

        prompt = (
            f"Du bist der STRATEGISCHE PLANER. Dein Ziel: Ein flüssiges, menschliches Gespräch.\n"
            f"User-Nachricht: '{user_text}'\n"
            f"Letzte Bot-Nachricht war: '{last_bot_msg}'\n"
            f"Anzahl Nachrichten im Verlauf: {msg_count}\n\n"
            
            "!!! REGELN FÜR DEN GESPRÄCHSVERLAUF !!!\n\n"
            
            "1. DER ANFANG (Nachricht 0-3):\n"
            "   - Wenn User 'Hi'/'Hallo' schreibt -> Antworte NUR mit Gruß + 'Alles fit?' oder 'Was geht?'.\n"
            "   - VERBOT: Erzähl KEINE random Storys (Kuchen, Wetter) zur Begrüßung. Das wirkt irre.\n\n"
            
            "2. BEIM THEMA BLEIBEN:\n"
            "   - Wenn ihr gerade über ein Thema redet (z.B. Filme, Arbeit), BLEIB DABEI.\n"
            "   - Wechsele das Thema NICHT, nur weil der User kurz 'ja' oder 'cool' schreibt. Das ist normale Zustimmung.\n"
            "   - Antworte dann einfach bestätigend: 'Fand ich auch.', 'Isso.', 'Voll.' (KEINE FRAGE).\n\n"
            
            "3. DAS 'RANDOM STORY' WERKZEUG:\n"
            "   - Nutze 'Ich hab grad Kuchen gebacken' oder 'War spazieren' NUR, wenn das Gespräch WIRKLICH tot ist (User schreibt gar nix mehr Sinnvolles) UND ihr schon länger schreibt (>5 Nachrichten).\n"
            "   - Sonst wirkt es wie ADHS.\n\n"
            
            "4. FINANZEN:\n"
            "   - Nur bei expliziten Triggern (Geld, Job, Stress).\n\n"
            
            "AUFGABE: Gib dem Texter eine Regieanweisung.\n"
            "Szenario A (Start): 'User grüßt. Grüß locker zurück. Frag kurz 'Alles klar?'. KURZFASSEN.'\n"
            "Szenario B (Laufend): 'User stimmt zu. Bestätige das kurz ('Safe'). Kein neues Thema. KEINE FRAGE.'"
        )

        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.5 # Nüchtern und logisch
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Strategy Error: {e}")
        return "Sei locker."

# --- 1. DER ANALYST (DATA) ---
async def extract_facts_from_text(user_text):
    try:
        prompt = (
            f"Analysiere die Nachricht: '{user_text}'.\n"
            "Erstelle ein Profil. Trenne strikt zwischen 'facts', 'meta' und Müll.\n\n"
            "FILTER-REGELN:\n"
            "1. IGNORIERE SLANG: 'Safe', 'Jop', 'Jo' sind KEINE Namen!\n"
            "2. IGNORIERE BANALES: 'Essen', 'Klo', 'Netflix' (außer als Hobby).\n\n"
            "Output JSON: { 'facts': {}, 'meta': {} }"
        )
        
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0, 
            response_format={"type": "json_object"} 
        )
        return json.loads(response.choices[0].message.content)
    except: return {}

# --- Proaktiv ---
async def get_proactive_message(history_messages):
    # Wenn wir manuell triggern, schauen wir auch auf den Verlauf
    msg_count = len(history_messages)
    if msg_count < 2:
        instr = "Schreib einfach nur 'Hey' oder 'Na?'."
    else:
        instr = "Melde dich locker. Mach ein kurzes Statement zu deinem Tag. KEINE FRAGE."
        
    return await get_chatgpt_response(history_messages, strategic_instruction=instr)