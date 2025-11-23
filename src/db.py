import sqlite3
import datetime
from pathlib import Path

DB_PATH = Path("data/chat.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            joined_at TIMESTAMP,
            is_active BOOLEAN DEFAULT 1,
            human_mode BOOLEAN DEFAULT 1,
            quiet_start INTEGER DEFAULT 0,
            quiet_end INTEGER DEFAULT 7
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            role TEXT,
            content TEXT,
            timestamp TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')
    # NEU: fact_type (fact oder meta)
    c.execute('''
        CREATE TABLE IF NOT EXISTS user_facts (
            user_id INTEGER,
            fact_key TEXT,
            fact_value TEXT,
            fact_type TEXT DEFAULT 'fact', 
            PRIMARY KEY (user_id, fact_key),
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')
    conn.commit()
    conn.close()

# --- User Management ---
def add_user(user_id, username, first_name):
    conn = get_connection()
    c = conn.cursor()
    now = datetime.datetime.now()
    c.execute("SELECT id FROM users WHERE id = ?", (user_id,))
    if c.fetchone() is None:
        c.execute("INSERT INTO users (id, username, first_name, joined_at, human_mode, quiet_start, quiet_end) VALUES (?, ?, ?, ?, 1, 0, 7)",
                  (user_id, username, first_name, now))
    else:
        c.execute("UPDATE users SET username = ?, first_name = ? WHERE id = ?",
                  (username, first_name, user_id))
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = get_connection()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return user

def toggle_user_active(user_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE users SET is_active = NOT is_active WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()

def is_user_active(user_id):
    user = get_user(user_id)
    if user: return bool(user['is_active'])
    return True

def toggle_human_mode(user_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE users SET human_mode = NOT human_mode WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()

def is_human_mode_on(user_id):
    user = get_user(user_id)
    if user: return bool(user['human_mode'])
    return False

def update_quiet_hours(user_id, start, end):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE users SET quiet_start = ?, quiet_end = ? WHERE id = ?", (start, end, user_id))
    conn.commit()
    conn.close()

# --- NEU: FAKTEN LOGIK MIT TYPEN ---
def add_fact(user_id, key, value, fact_type="fact"):
    """Speichert ein Faktum mit Typ"""
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO user_facts (user_id, fact_key, fact_value, fact_type) VALUES (?, ?, ?, ?)",
              (user_id, key, value, fact_type))
    conn.commit()
    conn.close()

def get_user_facts(user_id):
    """Gibt Fakten sortiert nach Typ zurück"""
    conn = get_connection()
    rows = conn.execute("SELECT fact_key, fact_value, fact_type FROM user_facts WHERE user_id = ?", (user_id,)).fetchall()
    conn.close()
    
    result = {
        "facts": {}, # Harte Fakten (Name, Ort...)
        "meta": {}   # Weiche Fakten (Stil, Stimmung...)
    }
    
    for row in rows:
        ftype = row['fact_type']
        if ftype not in result: ftype = "facts" # Fallback
        result[ftype][row['fact_key']] = row['fact_value']
        
    return result

def get_fact_value(user_id, key):
    conn = get_connection()
    row = conn.execute("SELECT fact_value FROM user_facts WHERE user_id = ? AND fact_key = ?", (user_id, key)).fetchone()
    conn.close()
    if row: return row['fact_value']
    return None

# --- Nachrichten ---
def save_message(user_id, role, content):
    conn = get_connection()
    c = conn.cursor()
    now = datetime.datetime.now()
    c.execute("INSERT INTO messages (user_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
              (user_id, role, content, now))
    conn.commit()
    conn.close()

def get_chat_history(user_id, limit=50):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT role, content, timestamp FROM messages WHERE user_id = ? ORDER BY id DESC LIMIT ?", (user_id, limit))
    rows = c.fetchall()
    conn.close()
    history = [{"role": row["role"], "content": row["content"], "timestamp": row["timestamp"]} for row in rows]
    return history[::-1]

def get_all_users():
    conn = get_connection()
    users = conn.execute("SELECT * FROM users ORDER BY joined_at DESC").fetchall()
    conn.close()
    return users

def get_full_chat(user_id):
    conn = get_connection()
    messages = conn.execute("SELECT * FROM messages WHERE user_id = ? ORDER BY timestamp ASC", (user_id,)).fetchall()
    conn.close()
    return messages