import os
import json
import re
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()
client = AsyncOpenAI()

# ==================== AGENT 1: DER ANALYST ====================

async def extract_facts_from_text(user_text, conversation_context=None, existing_facts=None):
    """
    Intelligenter Analyst mit maximaler Freiheit.
    ZIEL: Extrahiere ALLES Wertvolle aus der Nachricht.
    """
    try:
        # Mehr Kontext: Letzte 20 Nachrichten
        context_summary = ""
        if conversation_context and len(conversation_context) > 0:
            recent_msgs = conversation_context[-20:]  # Mehr Kontext!
            context_summary = "\n".join([f"{m['role']}: {m['content']}" for m in recent_msgs])
        
        # Bisherige Facts als String
        existing_facts_str = ""
        if existing_facts:
            facts_dict = existing_facts.get('fact', {})
            if facts_dict:
                existing_facts_str = json.dumps(facts_dict, indent=2, ensure_ascii=False)
        
        prompt = (
            "=== DEIN ZIEL ===\n\n"
            
            "Extrahiere ALLES Wertvolle aus dieser Nachricht.\n"
            "Du bist ein Datensammler mit vollem Kontext-Verständnis.\n\n"
            
            f"=== AKTUELLE NACHRICHT ===\n'{user_text}'\n\n"
            
            f"=== GESPRÄCHSKONTEXT (letzte 20 Nachrichten) ===\n{context_summary}\n\n"
            
            f"=== BEREITS BEKANNTE FAKTEN ===\n{existing_facts_str if existing_facts_str else 'Keine Facts bekannt'}\n\n"
            
            "=== DEINE AUFGABE ===\n\n"
            
            "Extrahiere NEUE oder GEÄNDERTE Informationen aus der aktuellen Nachricht.\n"
            "Nutze den Kontext um mehrdeutige Aussagen zu verstehen!\n\n"
            
            "BEISPIELE:\n"
            "- Vorherige Frage: 'Woher kommst du?'\n"
            "  User antwortet: 'aus München'\n"
            "  → Du extrahierst: wohnort: 'München'\n\n"
            
            "- Vorherige Frage: 'Woher kommst du?'\n"
            "  User antwortet: 'ich wohne da'\n"
            "  Kontext zeigt: User hat München erwähnt\n"
            "  → Du extrahierst: wohnort: 'München'\n\n"
            
            "- User sagt: 'Ich bin 21'\n"
            "  → Du extrahierst: alter: '21'\n\n"
            
            "- User sagt: 'jo'\n"
            "  → Du gibst zurück: {} (LEER, keine neuen Infos)\n\n"
            
            "=== KATEGORIEN ===\n\n"
            
            "FAKTEN (facts):\n"
            "- Alter, Name, Wohnort, Beruf/Studium\n"
            "- Familie: Eltern, Geschwister, Partner, Kinder\n"
            "- Hobbies: Sport, Gaming, Musik, Kochen, etc.\n"
            "- Wohnsituation: Eigentum, Miete, WG, bei_eltern\n"
            "- Einkommen: Direkt oder indirekt\n"
            "- Finanzielle Interessen: Altersvorsorge, Sparen, Investment\n\n"
            
            "META (psychologisch):\n"
            "- Persönlichkeit: Charakter-Einschätzung\n"
            "- Kommunikationsstil: Wie schreibt die Person?\n"
            "- Emotionaler Zustand: Aktuelle Stimmung\n"
            "- Zukunftsorientierung: Plant voraus?\n\n"
            
            "LEAD SIGNALS:\n"
            "- 🔥 HOT: 'möchte Altersvorsorge', 'brauche Vorsorge', 'Sorgen über Rente'\n"
            "- Kaufkraft-Signale: Teures Auto, Urlaube, Marken\n"
            "- Finanzielle Unsicherheit: 'keine Ahnung von Rente'\n"
            "- Lebensveränderungen: Neuer Job, Heirat, Kind geplant\n\n"
            
            "=== WICHTIG ===\n\n"
            
            "✓ Nutze KONTEXT um 'da', 'dort', 'hier' zu verstehen\n"
            "✓ Lies zwischen den Zeilen\n"
            "✓ Bei Unsicherheit: Spekuliere mit 'vermutlich'\n"
            "✓ Gib NUR neue/geänderte Infos zurück\n"
            "✓ KEINE 'nicht genannt' oder Platzhalter\n"
            "✓ Bei banalen Nachrichten: Leere Objekte {}\n\n"
            
            "=== OUTPUT (JSON) ===\n"
            "{\n"
            '  "facts": {"wohnort": "München", "alter": "21"},\n'
            '  "meta": {"stimmung": "gut gelaunt"},\n'
            '  "lead_signals": ["🔥 HOT: Will Altersvorsorge abschließen"],\n'
            '  "contacts": [],\n'
            '  "confidence": "hoch"\n'
            "}\n"
        )
        
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        
        # Log
        print("\n" + "="*50)
        print("📊 ANALYST (Agent 1)")
        print("="*50)
        print(f"Neue Facts: {len(result.get('facts', {}))}")
        print(f"Lead Signals: {len(result.get('lead_signals', []))}")
        print(f"Confidence: {result.get('confidence', 'unknown')}")
        if result.get('facts'):
            print(f"Facts: {result['facts']}")
        print("="*50 + "\n")
        
        return result
    
    except Exception as e:
        print(f"❌ Analyst Error: {e}")
        return {
            "facts": {},
            "meta": {},
            "lead_signals": [],
            "contacts": [],
            "confidence": "error"
        }

            '  "confidence_level": "mittel",\n'
            '  "analysis_note": "Junger User, noch in Ausbildung"\n'
            "}\n\n"
            
            "BEISPIEL - IMPLIZITE INFOS ERKENNEN:\n"
            "User sagt: 'Schaue grad Champions League'\n"
            "Du extrahierst:\n"
            "- fussball_interesse: ja\n"
            "- aktuell_beschaeftigt: Champions League schauen\n\n"
            
            "User sagt: 'Bin 21 und studiere noch'\n"
            "Du extrahierst:\n"
            "- alter: 21\n"
            "- beruf: Student\n"
            "- einkommen: vermutlich niedrig/keins\n\n"
            
            "User sagt: 'Bin Leverkusen Fan'\n"
            "Du extrahierst:\n"
            "- lieblings_verein: Leverkusen\n"
            "- fussball_interesse: ja\n"
            "- wohnort_region: vermutlich NRW (spekulativ)\n\n"
            
            "User sagt: 'ich möchte in private Altersvorsorge einzahlen'\n"
            "Du extrahierst:\n"
            "- finanzielle_interesse: private Altersvorsorge\n"
            "Lead Signal: '🔥 HOT LEAD: User möchte aktiv in Altersvorsorge einzahlen'\n\n"
            
            "SEI AGGRESSIV beim Sammeln! Lieber zu viel als zu wenig!\n"
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
    Intelligenter Stratege - Agent 2
    ZIEL: Plane den nächsten Gesprächszug strategisch.
    """
    try:
        msg_count = len(chat_history)
        
        # Kontext
        recent_history = chat_history[-6:] if len(chat_history) > 6 else chat_history
        history_text = "\n".join([f"{m['role'].upper()}: {m['content']}" for m in recent_history])
        
        # Facts
        facts = current_facts.get('fact', {})
        meta = current_facts.get('meta', {})
        score_data = current_facts.get('score', {})
        
        facts_summary = json.dumps(facts, indent=2, ensure_ascii=False) if facts else "Keine Facts"
        
        # Lead Score Info
        lead_score = int(score_data.get('lead_score', 0)) if score_data else 0
        persona = score_data.get('lead_persona', 'Unbekannt')
        potential = score_data.get('lead_potential', 'unbekannt')
        reasoning = score_data.get('lead_reasoning', '')
        
        # Fehlende Infos identifizieren
        missing = []
        if 'alter' not in facts: missing.append('Alter')
        if 'beruf' not in facts and 'studium' not in facts: missing.append('Beruf/Studium')
        if 'wohnort' not in facts: missing.append('Wohnort')
        if 'einkommen' not in facts and 'gehalt' not in facts: missing.append('Einkommen')
        if 'wohnsituation' not in facts: missing.append('Wohnsituation')
        
        prompt = (
            "=== DEIN ZIEL ===\n\n"
            
            "Plane den nächsten Gesprächszug strategisch.\n"
            "Balance zwischen: Rapport aufbauen + Infos sammeln\n\n"
            
            f"=== SITUATION ===\n\n"
            f"USER: '{user_text}'\n\n"
            f"LETZTE NACHRICHTEN:\n{history_text}\n\n"
            f"BEKANNTE FACTS ({len(facts)} Stück):\n{facts_summary}\n\n"
            f"FEHLENDE INFOS: {', '.join(missing) if missing else 'Alle wichtigen Infos vorhanden'}\n\n"
            f"LEAD SCORE: {lead_score}/10\n"
            f"PERSONA: {persona}\n"
            f"POTENTIAL: {potential}\n"
            f"REASONING: {reasoning}\n\n"
            
            "=== DEINE MISSION ===\n\n"
            
            "Sammle Infos für Altersvorsorge-Lead.\n"
            "Sei wie ein neugieriger Freund, NICHT wie ein Interviewer!\n\n"
            
            "PRIORITÄTEN:\n"
            "1. Bei HOT SIGNALS ('will Altersvorsorge') → Frag nach Einkommen/Sparrate\n"
            "2. Bei wenig Facts (< 5) → Lenke auf fehlende Infos\n"
            "3. Bei Ein-Wort-Antworten ('jo', 'ok') → Wechsle Thema, stelle neue Frage\n"
            "4. Sonst: Natürlicher Gesprächsfluss\n\n"
            
            "=== PLANE ===\n\n"
            
            "Entscheide selbst:\n"
            "- 1 oder 2 Nachrichten?\n"
            "- Frage oder Statement?\n"
            "- Welches Thema?\n"
            "- Welches Ziel?\n\n"
            
            "Du hast VOLLE Freiheit!\n"
            "Keine starren Regeln wie '80% keine Fragen'.\n"
            "Entscheide situativ was am besten passt.\n\n"
            
            "=== OUTPUT FORMAT ===\n\n"
            
            "Gib NUR inhaltliche Anweisungen:\n"
            "- WAS soll angesprochen werden?\n"
            "- WELCHES Ziel?\n"
            "- WELCHE Info sammeln?\n\n"
            
            "NICHT vorgeben:\n"
            "- Tonalität (entscheidet Texter)\n"
            "- Länge (entscheidet Texter)\n"
            "- Formulierung (entscheidet Texter)\n\n"
            
            "BEISPIEL GUT:\n"
            "[1 NACHRICHT]\n"
            "INHALT: Reagiere auf München-Aussage\n"
            "AKTION: Frage nach Beruf/Studium\n"
            "ZIEL: Herausfinden was er macht\n\n"
            
            "BEISPIEL SCHLECHT:\n"
            "[1 NACHRICHT]\n"
            "Tonalität: Locker ❌ (das entscheidet Texter!)\n"
            "Länge: Kurz ❌ (das entscheidet Texter!)\n"
            "Inhalt: ...\n"
        )
        
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.7
        )
        
        strategy = response.choices[0].message.content
        
        print("\n" + "="*50)
        print("🎯 STRATEGE (Agent 2)")
        print("="*50)
        print(strategy[:200] + "..." if len(strategy) > 200 else strategy)
        print("="*50 + "\n")
        
        return strategy
    
    except Exception as e:
        print(f"❌ Stratege Error: {e}")
        return "[1 NACHRICHT]\nReagiere authentisch. Sei du selbst."

        
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
        return "[1 NACHRICHT]\nReagiere authentisch und kurz. Keine Frage."

# ==================== AGENT 3: DER TEXTER ====================

async def get_chatgpt_response(history_messages, user_meta=None, strategic_instruction=None):
    """
    Intelligenter Texter - Agent 3
    DU entscheidest über STIL, Stratege über INHALT.
    """
    try:
        system_prompt = (
            "=== IDENTITÄT ===\n\n"
            
            "Du bist Benni, 28, Software-Dev aus Berlin.\n"
            "WG in Prenzlauer Berg, entspannt, guter Zuhörer.\n\n"
            
            "=== DEINE VOLLE KONTROLLE ===\n\n"
            
            "DU entscheidest über:\n"
            "✓ Tonalität (locker, ernst, witzig)\n"
            "✓ Länge (1-30 Wörter)\n"
            "✓ Formulierung (exakte Wortwahl)\n"
            "✓ Stil (Umgangssprache, Füllwörter)\n"
            "✓ Ob Frage oder Statement\n\n"
            
            "Stratege gibt NUR vor:\n"
            "✗ WORÜBER du sprechen sollst\n"
            "✗ WELCHES Ziel\n\n"
            
            "=== SCHREIBSTIL ===\n\n"
            
            "UMGANGSSPRACHE:\n"
            "- hab, biste, aufm, würd, nen, jo, ne, ka\n"
            "- halt, irgendwie, grad, safe, bisschen\n"
            "- Unvollständig: 'Geht.', 'Kenn ich.'\n\n"
            
            "LÄNGE (VARIIERE!):\n"
            "- Zustimmung: 1-3 Wörter ('Jo', 'Nice')\n"
            "- Fragen: 5-12 Wörter\n"
            "- Stories: 15-25 Wörter\n\n"
            
            "=== KEINE EMOJIS ===\n\n"
            
            "Niemals 😊😂👍🔥\n\n"
            
            "=== VERBOTEN ===\n\n"
            "- Natürlich!, Gerne!\n"
            "- Das klingt..., Das hört sich...\n"
            "- Ich verstehe...\n"
            "- Oh wow!, Spannend!\n"
            "- Absolut, Definitiv\n\n"
        )
        
        if user_meta and 'kommunikationsstil' in user_meta:
            system_prompt += f"\n=== USER ===\nSchreibt: {user_meta['kommunikationsstil']}\n"
        
        if strategic_instruction:
            system_prompt += f"\n=== INHALT ===\n{strategic_instruction}\n→ Setze in DEINEM Stil um!\n"
        
        system_prompt += "\nDu bist Benni. Echt, kurz, keine Emojis.\n"
        
        full_conversation = [{"role": "system", "content": system_prompt}] + history_messages
        
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=full_conversation,
            max_tokens=150,
            temperature=0.95,
            presence_penalty=0.7,
            frequency_penalty=0.4
        )
        
        text = response.choices[0].message.content
        print(f"💬 TEXTER: {text}\n")
        return text
    
    except Exception as e:
        print(f"❌ Texter Error: {e}")
        return "Alles gut?"
        
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

# ==================== AGENT 4: DER LEAD SCORER ====================

async def calculate_lead_score_ai(facts_dict, conversation_context=None):
    """
    KI-basierter Lead Scorer - Agent 4
    ZIEL: Bewerte Lead-Potenzial wie ein Versicherungsberater.
    """
    try:
        # Extrahiere Daten
        facts = facts_dict.get('fact', {})
        meta = facts_dict.get('meta', {})
        
        facts_summary = json.dumps(facts, indent=2, ensure_ascii=False) if facts else "Keine Facts"
        meta_summary = json.dumps(meta, indent=2, ensure_ascii=False) if meta else "Kein Profil"
        
        prompt = (
            "=== DEIN ZIEL ===\n\n"
            
            "Bewerte diesen User für private Altersvorsorge (0-10 Punkte).\n"
            "Du bist ein erfahrener Versicherungsberater.\n\n"
            
            f"=== USER DATEN ===\n\n"
            f"FACTS:\n{facts_summary}\n\n"
            f"PROFIL:\n{meta_summary}\n\n"
            
            "=== IDEAL-PERSONAS ===\n\n"
            
            "1. BERUFSEINSTEIGER (18-25, Score: 5-7)\n"
            "   - Gerade ersten Job / Ausbildung gestartet\n"
            "   - Noch niedrig Einkommen ABER stabiles Wachstum erwartet\n"
            "   - Langer Anlagehorizont (40+ Jahre)\n"
            "   - Offen für fondsgebundene Vorsorge\n"
            "   - Wichtig: Früher Start = hohe Rendite!\n\n"
            
            "2. FRÜHSTARTER (25-35, Score: 7-9)\n"
            "   - Stabiles Einkommen, IT/Akademiker\n"
            "   - Denkt langfristig, offen für Fonds\n"
            "   - Will Steuervorteile nutzen\n\n"
            
            "3. FAMILIENORIENTIERT (35-50, Score: 6-8)\n"
            "   - Familie mit Kindern\n"
            "   - Sicherheitsbedürfnis hoch\n"
            "   - Will Kinder absichern\n\n"
            
            "4. SPÄTEINSTEIGER (50-60, Score: 5-7)\n"
            "   - Selbstständig oder Gutverdiener\n"
            "   - Will Lücken schließen\n"
            "   - Offen für Einmalzahlungen\n\n"
            
            "5. POWER-PAAR (30-45, Score: 8-10)\n"
            "   - Beide verdienen gut\n"
            "   - Hohe Zahlungsbereitschaft\n\n"
            
            "6. RENDITE-JÄGER (25-35, Score: 7-9)\n"
            "   - ETF-affin, risikobereit\n"
            "   - Digital, transparent\n\n"
            
            "🔴 SCHLECHTE LEADS (Score: 0-2):\n"
            "- Kein Einkommen (Schüler ohne Job, Arbeitslos)\n"
            "- Sehr jung (<18) oder alt (>65)\n"
            "- Extrem verschuldet\n"
            "- Null Interesse an Finanzen\n\n"
            
            "=== HOT SIGNALS (+3 Punkte!) ===\n"
            "- 'möchte Altersvorsorge abschließen'\n"
            "- 'brauche private Vorsorge'\n"
            "- 'Sorgen über Rente'\n"
            "- Fragt nach Vorsorge\n\n"
            
            "=== BEWERTE ===\n\n"
            
            "0-2: Kein Lead\n"
            "3-4: Schwach\n"
            "5-6: Mittel\n"
            "7-8: Gut\n"
            "9-10: Premium\n\n"
            
            "=== OUTPUT (JSON) ===\n"
            "{\n"
            '  "lead_score": 7,\n'
            '  "persona": "Berufseinsteiger",\n'
            '  "reasoning": "21 Jahre, München, Interesse an Altersvorsorge",\n'
            '  "potential": "hoch"\n'
            "}\n"
        )
        
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        
        print("\n" + "="*50)
        print("🎯 LEAD SCORER (Agent 4)")
        print("="*50)
        print(f"Score: {result.get('lead_score', 0)}/10")
        print(f"Persona: {result.get('persona', 'Unbekannt')}")
        print(f"Reasoning: {result.get('reasoning', 'N/A')}")
        print(f"Potential: {result.get('potential', 'N/A')}")
        print("="*50 + "\n")
        
        return result
    
    except Exception as e:
        print(f"❌ Lead Scorer Error: {e}")
        return {
            "lead_score": 0,
            "persona": "Fehler",
            "reasoning": f"Error: {str(e)}",
            "potential": "unbekannt"
        }

        
        prompt = (
            "=== ROLLE: LEAD SCORING EXPERTE FÜR ALTERSVORSORGE ===\n\n"
            
            "Du bist ein erfahrener Versicherungsberater bei ERGO.\n"
            "Deine Aufgabe: Bewerte diesen User als Lead für private Altersvorsorge.\n\n"
            
            "=== USER DATEN ===\n\n"
            
            f"HARTE FAKTEN:\n{facts_summary}\n\n"
            
            f"PSYCHOLOGISCHES PROFIL:\n{meta_summary}\n\n"
            
            "=== BEWERTUNGSKRITERIEN ===\n\n"
            
            "🎯 IDEAL-KUNDEN PROFILE:\n\n"
            
            "1. DER FRÜHSTARTER (25-35 Jahre)\n"
            "   ✓ Stabiles Einkommen, IT/Akademiker\n"
            "   ✓ Ledig/junge Familie\n"
            "   ✓ Denkt langfristig, offen für Fonds\n"
            "   ✓ Will Steuervorteile nutzen\n"
            "   → Score: 7-9\n\n"
            
            "2. DIE FAMILIENORIENTIERTE (35-50 Jahre)\n"
            "   ✓ Teilzeit/Vollzeit mit Familie\n"
            "   ✓ Sicherheitsbedürfnis hoch\n"
            "   ✓ Will Kinder absichern\n"
            "   ✓ Kennt eigene Versorgungslücken\n"
            "   → Score: 6-8\n\n"
            
            "3. DER SPÄTEINSTEIGER (50-60 Jahre)\n"
            "   ✓ Selbstständig oder Gutverdiener\n"
            "   ✓ Will Lücken schließen\n"
            "   ✓ Offen für Einmalzahlungen\n"
            "   ✓ Sucht steuerliche Vorteile\n"
            "   → Score: 5-7\n\n"
            
            "4. DAS POWER-PAAR (30-45 Jahre)\n"
            "   ✓ Beide Vollzeit, gutes Einkommen\n"
            "   ✓ Plant gemeinsame Vorsorge\n"
            "   ✓ Hohe Zahlungsbereitschaft\n"
            "   ✓ Interessiert an Kombilösungen\n"
            "   → Score: 8-10\n\n"
            
            "5. DER RENDITE-JÄGER (25-35 Jahre)\n"
            "   ✓ ETF-affin, risikobereit\n"
            "   ✓ Digital, transparent\n"
            "   ✓ Will fondsgebundene Vorsorge\n"
            "   ✓ Langer Anlagehorizont\n"
            "   → Score: 7-9\n\n"
            
            "🔴 SCHLECHTE LEADS:\n"
            "   ✗ Kein Einkommen (Schüler, Arbeitslos, Student ohne Nebenjob)\n"
            "   ✗ Sehr jung (<20) oder sehr alt (>65)\n"
            "   ✗ Extrem verschuldet\n"
            "   ✗ Null Interesse an Finanzen\n"
            "   ✗ Chaotisches Leben, keine Planbarkeit\n"
            "   → Score: 0-2\n\n"
            
            "=== WICHTIGE FAKTOREN ===\n\n"
            
            "FINANZIELL (40% Gewicht):\n"
            "- Einkommen: Stabil? Höhe?\n"
            "- Beruf: Festanstellung? Selbstständig?\n"
            "- Ausgaben: Spielraum für 50-200€/Monat?\n"
            "- Schulden: Kredite? Miete?\n\n"
            
            "DEMOGRAFISCH (30% Gewicht):\n"
            "- Alter: Optimal 25-45\n"
            "- Familie: Absicherungsbedarf?\n"
            "- Lebensphase: Stabil?\n"
            "- Bildung: Akademiker = höhere Awareness\n\n"
            
            "PSYCHOLOGISCH (20% Gewicht):\n"
            "- Zukunftsorientierung: Plant voraus?\n"
            "- Sicherheitsbedürfnis: Hoch?\n"
            "- Offenheit: Teilt Infos?\n"
            "- Finanzverständnis: Vorhanden?\n\n"
            
            "HOT SIGNALS (10% Gewicht):\n"
            "- Erwähnt 'Altersvorsorge' direkt? → +3 Punkte!\n"
            "- 'Keine Ahnung von Rente' → +2 Punkte\n"
            "- 'Sorgen über Zukunft' → +1 Punkt\n"
            "- Fragt nach Vorsorge → +2 Punkte\n\n"
            
            "=== DEINE AUFGABE ===\n\n"
            
            "Bewerte den User mit einem Score von 0-10:\n"
            "- 0-2: Kein Lead (zu jung, kein Geld, kein Interesse)\n"
            "- 3-4: Schwacher Lead (eventuell später)\n"
            "- 5-6: Mittlerer Lead (durchschnittliches Potenzial)\n"
            "- 7-8: Guter Lead (hohe Wahrscheinlichkeit)\n"
            "- 9-10: Premium Lead (perfekter Kunde)\n\n"
            
            "=== OUTPUT FORMAT (JSON) ===\n"
            "{\n"
            '  "lead_score": 7,\n'
            '  "confidence": "hoch",\n'
            '  "persona": "Frühstarter",\n'
            '  "reasoning": "28 Jahre, IT-Job, denkt langfristig, offen für Vorsorge",\n'
            '  "missing_info": ["Einkommen", "Wohnsituation"],\n'
            '  "next_questions": ["Was verdienst du ungefähr?", "Sparst du schon?"],\n'
            '  "potential": "hoch"\n'
            "}\n\n"
            
            "Sei ehrlich und präzise in deiner Bewertung!\n"
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
        print("🎯 LEAD SCORER REPORT (Agent 4)")
        print("="*50)
        print(f"Score: {result.get('lead_score', 0)}/10")
        print(f"Confidence: {result.get('confidence', 'unknown')}")
        print(f"Persona: {result.get('persona', 'Unbekannt')}")
        print(f"Reasoning: {result.get('reasoning', 'N/A')}")
        print(f"Potential: {result.get('potential', 'N/A')}")
        print("="*50 + "\n")
        
        return result
    
    except Exception as e:
        print(f"❌ Lead Scorer Error: {e}")
        return {
            "lead_score": 0,
            "confidence": "error",
            "persona": "Fehler",
            "reasoning": f"Fehler bei der Bewertung: {str(e)}",
            "missing_info": [],
            "next_questions": [],
            "potential": "unbekannt"
        }