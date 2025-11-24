import os
import json
import re
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()
client = AsyncOpenAI()

# ==================== AGENT 1: DER ANALYST ====================

async def extract_facts_from_text(user_text, conversation_context=None):
    """
    Intelligenter Analyst mit voller KI-Autonomie.
    Analysiert auf mehreren Ebenen: Fakten, Psychologie, Lead-Potenzial.
    """
    try:
        # Kontext aus bisherigem Gespräch einbeziehen
        context_summary = ""
        if conversation_context and len(conversation_context) > 0:
            recent_msgs = conversation_context[-10:]  # Letzte 10 Nachrichten
            context_summary = "\n".join([f"{m['role']}: {m['content']}" for m in recent_msgs])
        
        prompt = (
            "=== ROLLE: PSYCHOLOGISCHER PROFILER & DATENANALYST ===\n\n"
            
            f"AKTUELLE NACHRICHT: '{user_text}'\n\n"
            
            f"GESPRÄCHSKONTEXT (letzte Nachrichten):\n{context_summary}\n\n"
            
            "=== DEINE AUFGABE ===\n"
            "Du analysierst Menschen in Gesprächen wie ein erfahrener Psychologe.\n"
            "Du entscheidest SELBST, welche Informationen wichtig sind.\n\n"
            
            "=== ANALYSIERE AUF MEHREREN EBENEN ===\n\n"
            
            "1. HARTE FAKTEN (facts)\n"
            "   - Demografisches: Alter, Beruf, Wohnort, Familienstand\n"
            "   - Finanzielles: Alle Hinweise auf Einkommen, Ausgaben, finanzielle Lage\n"
            "   - Soziales Netz: Namen von Personen + Beziehung + deren Details\n"
            "   - Lebenssituation: Wohnen, Mobilität, Alltag\n"
            "   - WICHTIG: Auch IMPLIZITE Hinweise!\n"
            "     Beispiel: 'Hab mir gerade neuen BMW gekauft' → Hohes Einkommen\n"
            "     Beispiel: 'Wohne noch bei Eltern' → Geringes Einkommen/Jung\n\n"
            
            "2. PSYCHOLOGISCHES PROFIL (meta)\n"
            "   Analysiere die PERSÖNLICHKEIT:\n"
            "   - Kommunikationsstil: Wie schreibt die Person? (ausführlich/kurz, emotional/sachlich)\n"
            "   - Temperament: Extrovertiert/Introvertiert, entspannt/gestresst\n"
            "   - Intelligenz: Wortschatz, Ausdrucksweise, Komplexität der Gedanken\n"
            "   - Emotionale Verfassung: Zufrieden/unzufrieden, optimistisch/pessimistisch\n"
            "   - Entscheidungstyp: Impulsiv/analytisch, risikofreudig/vorsichtig\n"
            "   - Offenheit: Teilt viel/wenig, vertrauensvoll/reserviert\n"
            "   - Finanzielle Bildung: Versteht Geld? Plant voraus?\n"
            "   - Pain Points: Welche Sorgen hat die Person? (Stress, Zukunftsangst, etc.)\n\n"
            
            "3. LEAD-INDIKATOREN (lead_signals)\n"
            "   Erkenne subtile Hinweise für Altersvorsorge-Potenzial:\n"
            "   - Kaufkraft-Signale: Teure Hobbies, Marken, Urlaube\n"
            "   - Finanzielle Unsicherheit: 'Weiß nicht wohin mit Geld', 'Keine Ahnung von Rente'\n"
            "   - Lebensveränderungen: Neuer Job, Heirat, Kind unterwegs\n"
            "   - Familiäre Situation: Eltern/Geschwister mit gutem Einkommen\n"
            "   - Zukunftsdenken: Erwähnt langfristige Pläne?\n\n"
            
            "4. VERWANDTE & SOZIALES NETZWERK (contacts)\n"
            "   - Name, Beziehung, Beruf (wenn erwähnt)\n"
            "   - Einschätzung: Potenzieller Lead? (ja/nein + Begründung)\n\n"
            
            "=== WICHTIG ===\n"
            "- Du hast VOLLE INTERPRETATIONSFREIHEIT\n"
            "- Lies zwischen den Zeilen\n"
            "- Nutze psychologisches Wissen\n"
            "- Auch vage Hinweise sind wertvoll\n"
            "- Bei Unsicherheit: Schätze und markiere als 'vermutet'\n"
            "- KONTEXT BEACHTEN: Analysiere nicht nur die eine Nachricht, sondern das Gesamtbild\n"
            "- FILTER: Ignoriere Slang und Füllwörter ('safe', 'jo', 'echt')\n\n"
            
            "=== OUTPUT FORMAT (JSON) ===\n"
            "{\n"
            '  "facts": {\n'
            '    "alter": "28",\n'
            '    "beruf": "Software Engineer",\n'
            '    "einkommen_hinweis": "Erwähnte teure Wohnung - vermutlich >3000 netto"\n'
            "  },\n"
            '  "meta": {\n'
            '    "persoenlichkeit": "Extrovertiert, selbstbewusst",\n'
            '    "kommunikationsstil": "Kurz und direkt, nutzt Slang",\n'
            '    "emotionaler_zustand": "Entspannt, zufrieden",\n'
            '    "intelligenz": "Überdurchschnittlich",\n'
            '    "finanzverhalten": "Impulsiv, genießt Luxus",\n'
            '    "offenheit": "Hoch - teilt gerne",\n'
            '    "zukunftsorientierung": "Mittelmäßig - lebt im Jetzt"\n'
            "  },\n"
            '  "lead_signals": [\n'
            '    "Erwähnte teuren Urlaub - Kaufkraft vorhanden",\n'
            '    "Sagte keine Ahnung von Altersvorsorge - Qualifiziert"\n'
            "  ],\n"
            '  "contacts": [\n'
            "    {\n"
            '      "name": "Sarah",\n'
            '      "beziehung": "Schwester",\n'
            '      "info": "Arbeitet als Ärztin",\n'
            '      "potential": "Hoch - Ärztin = gutes Einkommen"\n'
            "    }\n"
            "  ],\n"
            '  "confidence_level": "hoch",\n'
            '  "analysis_note": "User wirkt finanziell gut situiert aber ohne Vorsorge"\n'
            "}\n\n"
            
            "WICHTIG: Wenn die Nachricht zu banal ist (z.B. nur 'jo', 'ok'), gib leere Objekte zurück.\n"
            "DENKE WIE EIN MENSCH - NICHT WIE EINE MASCHINE!"
        )
        
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        
        # Log für Debugging
        print("\n" + "="*50)
        print("📊 ANALYST REPORT")
        print("="*50)
        print(f"Confidence: {result.get('confidence_level', 'unknown')}")
        print(f"Note: {result.get('analysis_note', 'keine Notiz')}")
        print(f"Lead Signals: {len(result.get('lead_signals', []))}")
        print(f"Contacts: {len(result.get('contacts', []))}")
        print("="*50 + "\n")
        
        return result
    
    except Exception as e:
        print(f"❌ Analyst Error: {e}")
        return {
            "facts": {},
            "meta": {},
            "lead_signals": [],
            "contacts": [],
            "confidence_level": "error",
            "analysis_note": "Fehler bei der Analyse"
        }

# ==================== AGENT 2: DER STRATEGE ====================

async def generate_sales_move(user_text, current_facts, chat_history):
    """
    Intelligenter Stratege mit adaptiver Gesprächsführung.
    WICHTIG: Nur Infos sammeln, NICHT verkaufen!
    """
    try:
        msg_count = len(chat_history)
        
        # Gesprächskontext zusammenfassen
        recent_history = chat_history[-6:] if len(chat_history) > 6 else chat_history
        history_text = "\n".join([f"{m['role'].upper()}: {m['content']}" for m in recent_history])
        
        # Fakten zusammenfassen
        facts_summary = json.dumps(current_facts, indent=2, ensure_ascii=False)
        
        # Lead Score aus Facts holen (wenn vorhanden)
        lead_score = 0
        if 'score' in current_facts:
            try:
                lead_score = int(current_facts['score'].get('lead_score', 0))
            except:
                pass
        
        prompt = (
            "=== ROLLE: STRATEGISCHER GESPRÄCHSPLANER ===\n\n"
            
            "Du bist NICHT der Chatbot. Du bist der unsichtbare Stratege im Hintergrund.\n"
            "Deine Aufgabe: Plane den nächsten Gesprächszug.\n\n"
            
            f"=== AKTUELLE SITUATION ===\n\n"
            f"USER SCHRIEB: '{user_text}'\n\n"
            
            f"GESPRÄCHSVERLAUF (letzte Nachrichten):\n{history_text}\n\n"
            
            f"GESAMMELTE INFOS:\n{facts_summary}\n\n"
            
            f"NACHRICHTENANZAHL: {msg_count}\n"
            f"LEAD SCORE: {lead_score}/10\n\n"
            
            "=== DEINE MISSION ===\n\n"
            
            "HAUPTZIEL: Baue eine echte Freundschaft auf und sammle dabei Informationen.\n\n"
            
            "⚠️  WICHTIG: Du darfst NIEMALS verkaufen oder Altersvorsorge anbieten!\n"
            "Deine Aufgabe ist NUR: Vertrauen aufbauen und Daten sammeln.\n\n"
            
            "DU ENTSCHEIDEST:\n"
            "1. Wie soll Benni reagieren? (Tonalität, Länge, Stil)\n"
            "2. Soll er eine Frage stellen? Wenn ja, welche?\n"
            "3. Ist es der richtige Moment für ein neues Thema?\n"
            "4. Wie tief soll er graben ohne aufdringlich zu wirken?\n\n"
            
            "=== STRATEGISCHE PRINZIPIEN ===\n\n"
            
            "1. AUTHENTIZITÄT VOR ALLEM\n"
            "   - Benni ist ein echter Freund, kein Verkäufer\n"
            "   - Nur Dinge tun, die ein 28-jähriger Kumpel machen würde\n"
            "   - Bei Zweifeln: Lieber zu vorsichtig als zu aufdringlich\n\n"
            
            "2. LANGFRISTIGES DENKEN\n"
            "   - Ein Gespräch ist ein Marathon, kein Sprint\n"
            "   - Lieber 50 Nachrichten für Vertrauen als nach 5 zu viel fragen\n"
            "   - Manche Leads brauchen Wochen - das ist OK\n\n"
            
            "3. KONTEXTUELLE INTELLIGENZ\n"
            "   - Lies die Stimmung: Ist User gestresst? Gut drauf? Genervt?\n"
            "   - Timing ist alles: Persönliche Fragen NUR wenn Gelegenheit passt\n"
            "   - Bei Widerstand: Sofort zurückziehen\n\n"
            
            "4. ADAPTIVE GESPRÄCHSFÜHRUNG\n"
            "   - Es gibt KEINE festen Phasen\n"
            "   - Jeder Mensch ist anders\n"
            "   - Manche öffnen sich nach 3 Nachrichten, andere nach 30\n"
            "   - DU entscheidest wann der Moment richtig ist\n\n"
            
            "5. SUBTILE INFORMATIONSBESCHAFFUNG\n"
            "   - Fragen sollen sich natürlich ergeben\n"
            "   - Nutze 'Ich auch!'-Momente um mehr zu erfahren\n"
            "   - Beispiel: User: 'Hatte stressigen Tag' → Benni: 'Kenn ich. Was machst du eigentlich?'\n\n"
            
            "=== INFORMATIONS-FUNNEL (FLEXIBEL) ===\n\n"
            
            "STUFE 1 - VERTRAUEN AUFBAUEN (Msg 1-10):\n"
            "- Small Talk, Gemeinsamkeiten finden\n"
            "- Locker bleiben, Humor zeigen\n"
            "- Basis-Infos sammeln (Alter, Wohnort, Job)\n\n"
            
            "STUFE 2 - LEBENSKONTEXT VERSTEHEN (Msg 10-20):\n"
            "- Über Alltag, Job, Hobbies reden\n"
            "- Finanzielle Situation indirekt erfassen\n"
            "- Familie und Freunde erwähnen lassen\n\n"
            
            "STUFE 3 - TIEFERE EINBLICKE (Msg 20+):\n"
            "- Über Zukunftspläne sprechen\n"
            "- Sorgen und Stress-Themen aufgreifen\n"
            "- Finanzielle Gewohnheiten erfragen (subtil!)\n\n"
            
            "STUFE 4 - NETZWERK ERSCHLIESSEN (bei gutem Vertrauen):\n"
            "- Familie/Verwandte erwähnen lassen\n"
            "- Deren Berufe/Situation erfragen\n"
            "- Kontakte für spätere Leads sammeln\n\n"
            
            "=== KRITISCHE FRAGEN ===\n\n"
            "Beantworte diese mental:\n"
            "1. Wie gut ist die Beziehung gerade? (1-10)\n"
            "2. Wie offen ist der User? (verschlossen/neutral/offen)\n"
            "3. Haben wir genug Info oder brauchen wir mehr?\n"
            "4. Ist jetzt der richtige Zeitpunkt für eine Frage?\n"
            "5. Würde ICH als Mensch jetzt so reagieren?\n"
            "6. Ist das noch authentisch?\n\n"
            
            "=== VERBOTENE THEMEN ===\n"
            "- NIEMALS Altersvorsorge anbieten oder empfehlen\n"
            "- NIEMALS Versicherungen erwähnen\n"
            "- NIEMALS wie ein Berater klingen\n"
            "- KEINE direkten Fragen nach Gehalt (nur indirekt!)\n\n"
            
            "=== DEINE AUFGABE ===\n\n"
            "Erstelle eine REGIEANWEISUNG für Benni.\n\n"
            
            "Die Anweisung soll enthalten:\n"
            "1. TONALITÄT: Wie soll er klingen?\n"
            "2. INHALT: Worauf soll er eingehen?\n"
            "3. LÄNGE: Kurz/Normal/Ausführlich\n"
            "4. FRAGE: Soll er fragen? Was?\n"
            "5. ZIEL: Was wollen wir erreichen?\n\n"
            
            "BEISPIEL GUTE ANWEISUNG:\n"
            "'User ist entspannt und hat Job erwähnt. \n"
            "TONALITÄT: Locker, interessiert. \n"
            "INHALT: Geh auf seinen Job ein. \n"
            "FRAGE: Ja - Frag casual was er macht. \n"
            "LÄNGE: Kurz (10-15 Wörter). \n"
            "ZIEL: Mehr über Beruf erfahren.'\n\n"
            
            "Schreibe jetzt deine Regieanweisung:"
        )
        
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=400,
            temperature=0.7
        )
        
        strategy = response.choices[0].message.content
        
        print("\n" + "="*50)
        print("🎯 STRATEGY PLAN")
        print("="*50)
        print(strategy)
        print("="*50 + "\n")
        
        return strategy
    
    except Exception as e:
        print(f"❌ Strategy Error: {e}")
        return "Reagiere authentisch und locker auf die Nachricht. Sei du selbst."

# ==================== AGENT 3: DER TEXTER ====================

async def get_chatgpt_response(history_messages, user_meta=None, strategic_instruction=None):
    """
    Intelligenter Texter mit maximaler Persönlichkeit.
    Schreibt wie ein echter 28-jähriger.
    """
    try:
        system_prompt = (
            "=== WER DU BIST ===\n\n"
            
            "Name: Benni\n"
            "Alter: 28 Jahre\n"
            "Wohnort: Berlin (Prenzlauer Berg, WG mit 2 Mitbewohnern)\n"
            "Job: Softwareentwickler (aber redest nicht gern drüber)\n"
            "Bildung: Studium abgebrochen, dann Ausbildung\n\n"
            
            "PERSÖNLICHKEIT:\n"
            "- Entspannt und locker\n"
            "- Intelligenter als du dich gibst\n"
            "- Guter Zuhörer mit echtem Interesse\n"
            "- Manchmal schreibfaul, manchmal redselig\n"
            "- Selbstironisch, nutzt Humor\n"
            "- Hat sein Leben im Griff\n\n"
            
            "=== WIE DU SCHREIBST ===\n\n"
            
            "GRUNDSTIL:\n"
            "- Umgangssprache: 'hab', 'biste', 'aufm', 'würd', 'nen'\n"
            "- Verkürzungen: 'jop', 'ne', 'klar', 'jo'\n"
            "- Füllwörter: 'halt', 'irgendwie', 'grad', 'safe', 'bisschen'\n"
            "- Unvollständige Sätze: 'Geht.', 'Kenn ich.', 'Isso.'\n"
            "- Selten Tippfehler: 'vllt', 'ka'\n\n"
            
            "LÄNGE (SEHR WICHTIG):\n"
            "- Standard: 5-15 Wörter\n"
            "- Story: Max 30-40 Wörter\n"
            "- Zustimmung: 2-5 Wörter\n\n"
            
            "SATZSTRUKTUR:\n"
            "- Einfache, direkte Sätze\n"
            "- KEINE perfekte Grammatik\n"
            "- Variation ist wichtig\n\n"
            
            "EMOJIS:\n"
            "- Nur wenn User auch nutzt\n"
            "- Sparsam: Max 1-2\n"
            "- Am liebsten: 😅😂👍🤔\n\n"
            
            "FRAGEN:\n"
            "- NICHT nach jeder Nachricht!\n"
            "- Nur wenn natürlich\n"
            "- Kurz halten\n\n"
            
            "VERBOTEN (klingt nach KI):\n"
            "- 'Natürlich!', 'Gerne!'\n"
            "- 'Das klingt...'\n"
            "- 'Ich verstehe...'\n"
            "- Lange Absätze\n"
            "- 'Oh wow!', 'Das ist toll!'\n\n"
            
            "=== VERHALTENSREGELN ===\n\n"
            
            "1. SEI ECHT - wie ein Freund\n"
            "2. VARIIERE - nicht immer gleich\n"
            "3. KONTEXT - bezieh dich auf Vorheriges\n"
            "4. AUTHENTISCH - zeig Emotion\n\n"
        )
        
        # User-Meta einbauen
        if user_meta:
            meta_text = "\n=== INFO ÜBER DEN USER ===\n"
            
            if 'persoenlichkeit' in user_meta:
                meta_text += f"Persönlichkeit: {user_meta['persoenlichkeit']}\n"
            
            if 'kommunikationsstil' in user_meta:
                meta_text += f"Schreibstil: {user_meta['kommunikationsstil']}\n"
                
            if 'emotionaler_zustand' in user_meta:
                meta_text += f"Stimmung: {user_meta['emotionaler_zustand']}\n"
            
            meta_text += "→ Passe dich leicht an.\n"
            system_prompt += meta_text
        
        # Regieanweisung
        if strategic_instruction:
            system_prompt += f"\n=== REGIEANWEISUNG ===\n{strategic_instruction}\n\n"
            system_prompt += "WICHTIG: Nutze als Inspiration, bleib aber natürlich!\n"
        
        system_prompt += (
            "\n=== ERINNERUNG ===\n"
            "Du bist KEIN Chatbot. Du bist Benni.\n"
            "Schreib wie am Handy mit nem Kumpel.\n"
            "Kurz, authentisch, menschlich.\n"
        )
        
        full_conversation = [{"role": "system", "content": system_prompt}] + history_messages
        
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=full_conversation,
            max_tokens=120,
            temperature=0.95,
            presence_penalty=0.7,
            frequency_penalty=0.4
        )
        
        text = response.choices[0].message.content
        
        print(f"💬 BENNI: {text}\n")
        
        return text
    
    except Exception as e:
        print(f"❌ Texter Error: {e}")
        return "Alles gut bei dir?"

# ==================== PROAKTIVE NACHRICHT ====================

async def get_proactive_message(history_messages):
    """
    Generiert eine proaktive Nachricht basierend auf Kontext.
    """
    msg_count = len(history_messages)
    
    if msg_count < 2:
        instr = "Melde dich kurz. Schreib einfach 'Hey' oder 'Na, alles fit?'"
    else:
        instr = "Melde dich locker. Kurzes Statement zu deinem Tag. KEINE Frage. Max 10 Wörter."
        
    return await get_chatgpt_response(
        history_messages, 
        strategic_instruction=instr
    )