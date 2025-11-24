import sys
import os
import requests
import asyncio
import json
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, redirect, url_for

# Path setup
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.db import (
    get_all_users, get_full_chat, get_user, toggle_user_active, 
    save_message, get_user_facts, toggle_human_mode, update_quiet_hours,
    get_user_stats, get_contacts, get_lead_signals
)
from src.bot import trigger_ai_message, set_global_token, calculate_lead_score

# Load environment
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if TELEGRAM_TOKEN:
    set_global_token(TELEGRAM_TOKEN)

# Flask App
app = Flask(__name__, template_folder='../templates')

# ==================== PAGES ====================

@app.route('/')
def index():
    """Dashboard Homepage mit User-Übersicht"""
    users = get_all_users()
    return render_template('index.html', users=users)

@app.route('/chat/<int:user_id>')
def chat_view(user_id):
    """Chat-Ansicht mit kompletter Akte"""
    all_users = get_all_users()
    current_user = get_user(user_id)
    messages = get_full_chat(user_id)
    facts = get_user_facts(user_id)
    
    return render_template(
        'chat.html', 
        user=current_user, 
        users=all_users, 
        messages=messages, 
        facts=facts
    )

@app.route('/settings/<int:user_id>')
def settings_view(user_id):
    """Einstellungs-Seite für Nachtruhe"""
    user = get_user(user_id)
    return render_template('settings.html', user=user)

@app.route('/save_settings/<int:user_id>', methods=['POST'])
def save_settings(user_id):
    """Speichert die Nachtruhe-Einstellungen"""
    try:
        start = int(request.form.get('start_hour'))
        end = int(request.form.get('end_hour'))
        
        # Validation
        if start < 0 or start > 23 or end < 0 or end > 23:
            return jsonify({"success": False, "error": "Ungültige Stunde"}), 400
        
        update_quiet_hours(user_id, start, end)
        print(f"✅ Nachtruhe aktualisiert für User {user_id}: {start}:00 - {end}:00")
        
    except Exception as e:
        print(f"❌ Fehler beim Speichern der Einstellungen: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
    
    return redirect(url_for('chat_view', user_id=user_id))

# ==================== API ENDPOINTS ====================

@app.route('/api/chat_data/<int:user_id>')
def get_chat_data(user_id):
    """
    Liefert alle Chat-Daten als JSON (für Live-Updates).
    Inkludiert: Messages, Facts, Meta, Lead Score, Toggles
    """
    try:
        # Messages
        raw_messages = get_full_chat(user_id)
        messages = []
        for msg in raw_messages:
            messages.append({
                "role": msg["role"],
                "content": msg["content"],
                "timestamp": msg["timestamp"].split('.')[0] if msg["timestamp"] else ""
            })
        
        # Facts (strukturiert)
        facts = get_user_facts(user_id)
        
        # Lead Score berechnen
        lead_score = calculate_lead_score(facts)
        
        # User Info
        user = get_user(user_id)
        
        return jsonify({
            "messages": messages,
            "facts": facts,
            "lead_score": lead_score,
            "is_active": bool(user['is_active']),
            "is_human": bool(user['human_mode'])
        })
    
    except Exception as e:
        print(f"❌ Fehler bei get_chat_data: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/user_stats/<int:user_id>')
def get_user_stats_api(user_id):
    """
    Liefert Statistiken über einen User.
    """
    try:
        stats = get_user_stats(user_id)
        facts = get_user_facts(user_id)
        lead_score = calculate_lead_score(facts)
        
        return jsonify({
            "messages": stats['messages'],
            "facts": stats['facts'],
            "contacts": stats['contacts'],
            "lead_score": lead_score
        })
    
    except Exception as e:
        print(f"❌ Fehler bei get_user_stats_api: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/user_details/<int:user_id>')
def get_user_details(user_id):
    """
    Liefert detaillierte User-Infos inkl. Kontakte und Signals.
    """
    try:
        facts = get_user_facts(user_id)
        contacts = get_contacts(user_id)
        signals = get_lead_signals(user_id)
        lead_score = calculate_lead_score(facts)
        
        return jsonify({
            "facts": facts,
            "contacts": contacts,
            "signals": signals,
            "lead_score": lead_score
        })
    
    except Exception as e:
        print(f"❌ Fehler bei get_user_details: {e}")
        return jsonify({"error": str(e)}), 500

# ==================== ACTIONS ====================

@app.route('/toggle/<int:user_id>', methods=['POST'])
def toggle_status(user_id):
    """Schaltet den KI-Aktiv-Status um"""
    try:
        toggle_user_active(user_id)
        user = get_user(user_id)
        status = "aktiviert" if user['is_active'] else "deaktiviert"
        print(f"✅ KI {status} für User {user_id}")
        return jsonify({"success": True, "is_active": bool(user['is_active'])})
    except Exception as e:
        print(f"❌ Fehler bei toggle_status: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/toggle_human/<int:user_id>', methods=['POST'])
def toggle_human(user_id):
    """Schaltet den Human Mode um"""
    try:
        toggle_human_mode(user_id)
        user = get_user(user_id)
        status = "aktiviert" if user['human_mode'] else "deaktiviert"
        print(f"✅ Human Mode {status} für User {user_id}")
        return jsonify({"success": True, "human_mode": bool(user['human_mode'])})
    except Exception as e:
        print(f"❌ Fehler bei toggle_human: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/trigger_ai/<int:user_id>', methods=['POST'])
def trigger_ai_route(user_id):
    """Löst eine proaktive KI-Nachricht aus (✨ Button)"""
    try:
        print(f"🎯 Triggere proaktive Nachricht für User {user_id}...")
        success = asyncio.run(trigger_ai_message(user_id))
        
        if success:
            return jsonify({"success": True, "message": "Nachricht gesendet"})
        else:
            return jsonify({"success": False, "error": "Konnte nicht senden"}), 500
    
    except Exception as e:
        print(f"❌ Fehler bei trigger_ai_route: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/send_message/<int:user_id>', methods=['POST'])
def send_manual_message(user_id):
    """Sendet eine manuelle Nachricht vom Dashboard"""
    try:
        text = request.form.get('message')
        
        if not text:
            return jsonify({"success": False, "error": "Keine Nachricht"}), 400
        
        if not TELEGRAM_TOKEN:
            return jsonify({"success": False, "error": "Kein Bot-Token"}), 500
        
        # Via Telegram API senden
        send_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            "chat_id": user_id,
            "text": text
        }
        
        response = requests.post(send_url, json=payload)
        
        if response.status_code == 200:
            # In DB speichern
            save_message(user_id, "assistant", text)
            print(f"✅ Manuelle Nachricht an User {user_id} gesendet")
            return jsonify({"success": True})
        else:
            print(f"❌ Telegram API Fehler: {response.text}")
            return jsonify({"success": False, "error": response.text}), 500
    
    except Exception as e:
        print(f"❌ Fehler bei send_manual_message: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Seite nicht gefunden"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Interner Serverfehler"}), 500

# ==================== MAIN ====================

if __name__ == '__main__':
    print("\n" + "="*50)
    print("🌐 WEB-DASHBOARD STARTET")
    print("="*50)
    print("📊 Dashboard: http://127.0.0.1:5000")
    print("⚠️  Debug Mode: Nur für Entwicklung!")
    print("="*50 + "\n")
    
    app.run(debug=True, port=5000, host='0.0.0.0')