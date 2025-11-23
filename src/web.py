import sys
import os
import requests
import asyncio
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, redirect, url_for

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.db import (
    get_all_users, get_full_chat, get_user, toggle_user_active, 
    save_message, get_user_facts, toggle_human_mode, update_quiet_hours
)
from src.bot import trigger_ai_message, set_global_token 

load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if TELEGRAM_TOKEN: set_global_token(TELEGRAM_TOKEN)

app = Flask(__name__, template_folder='../templates')

@app.route('/')
def index():
    users = get_all_users()
    return render_template('index.html', users=users)

@app.route('/chat/<int:user_id>')
def chat_view(user_id):
    all_users = get_all_users()
    current_user = get_user(user_id)
    messages = get_full_chat(user_id)
    # facts ist jetzt { 'facts': {...}, 'meta': {...} }
    facts = get_user_facts(user_id) 
    return render_template('chat.html', user=current_user, users=all_users, messages=messages, facts=facts)

@app.route('/settings/<int:user_id>')
def settings_view(user_id):
    user = get_user(user_id)
    return render_template('settings.html', user=user)

@app.route('/save_settings/<int:user_id>', methods=['POST'])
def save_settings(user_id):
    try:
        start = int(request.form.get('start_hour'))
        end = int(request.form.get('end_hour'))
        update_quiet_hours(user_id, start, end)
    except: pass
    return redirect(url_for('chat_view', user_id=user_id))

@app.route('/api/chat_data/<int:user_id>')
def get_chat_data(user_id):
    raw_messages = get_full_chat(user_id)
    messages = []
    for msg in raw_messages:
        messages.append({
            "role": msg["role"],
            "content": msg["content"],
            "timestamp": msg["timestamp"].split('.')[0] if msg["timestamp"] else ""
        })
    
    facts = get_user_facts(user_id) # Gibt strukturierte Fakten zurück
    user = get_user(user_id)
    return jsonify({
        "messages": messages, 
        "facts": facts, # JSON enthält jetzt 'facts' und 'meta' Keys
        "is_active": bool(user['is_active']), 
        "is_human": bool(user['human_mode'])
    })

@app.route('/toggle/<int:user_id>', methods=['POST'])
def toggle_status(user_id):
    toggle_user_active(user_id)
    return jsonify({"success": True})

@app.route('/toggle_human/<int:user_id>', methods=['POST'])
def toggle_human(user_id):
    toggle_human_mode(user_id)
    return jsonify({"success": True})

@app.route('/trigger_ai/<int:user_id>', methods=['POST'])
def trigger_ai_route(user_id):
    try:
        asyncio.run(trigger_ai_message(user_id))
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/send_message/<int:user_id>', methods=['POST'])
def send_manual_message(user_id):
    text = request.form.get('message')
    if text:
        send_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {"chat_id": user_id, "text": text}
        requests.post(send_url, json=payload)
        save_message(user_id, "assistant", text)
    return jsonify({"success": True})

if __name__ == '__main__':
    print("Starte Web-Dashboard auf http://127.0.0.1:5000")
    app.run(debug=True, port=5000)