import sqlite3
import datetime
import json
from pathlib import Path

DB_PATH = Path("data/chat.db")

def get_connection():
    """Erstellt eine Datenbankverbindung mit Row Factory"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialisiert die Datenbank mit allen benötigten Tabellen"""
    conn = get_connection()
    c = conn.cursor()
    
    # Users Tabelle
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            joined_at TIMESTAMP,
            is_active BOOLEAN DEFAULT 1,
            human_mode BOOLEAN DEFAULT 1,
            quiet_start INTEGER DEFAULT 23,
            quiet_end INTEGER DEFAULT 7,
            last_message_at TIMESTAMP
        )
    ''')
    
    # Messages Tabelle
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
    
    # User Facts Tabelle (erweitert)
    c.execute('''
        CREATE TABLE IF NOT EXISTS user_facts (
            user_id INTEGER,
            fact_key TEXT,
            fact_value TEXT,
            fact_type TEXT DEFAULT 'fact',
            updated_at TIMESTAMP,
            PRIMARY KEY (user_id, fact_key),
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')
    
    # Kontakte/Verwandte Tabelle (neu)
    c.execute('''
        CREATE TABLE IF NOT EXISTS user_contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name TEXT,
            relationship TEXT,
            info TEXT,
            potential TEXT,
            created_at TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')
    
    # Lead Signals Tabelle (neu)
    c.execute('''
        CREATE TABLE IF NOT EXISTS lead_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            signal TEXT,
            category TEXT,
            timestamp TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Datenbankstruktur erstellt")

# ==================== USER MANAGEMENT ====================

def add_user(user_id, username, first_name):
    """Fügt einen neuen User hinzu oder aktualisiert bestehenden"""
    conn = get_connection()
    c = conn.cursor()
    now = datetime.datetime.now()
    
    c.execute("SELECT id FROM users WHERE id = ?", (user_id,))
    if c.fetchone() is None:
        c.execute("""
            INSERT INTO users (id, username, first_name, joined_at, human_mode, quiet_start, quiet_end, last_message_at) 
            VALUES (?, ?, ?, ?, 1, 23, 7, ?)
        """, (user_id, username, first_name, now, now))
    else:
        c.execute("""
            UPDATE users 
            SET username = ?, first_name = ?, last_message_at = ?
            WHERE id = ?
        """, (username, first_name, now, user_id))
    
    conn.commit()
    conn.close()

def get_user(user_id):
    """Holt einen User aus der Datenbank"""
    conn = get_connection()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return user

def get_all_users():
    """Holt alle User sortiert nach letzter Aktivität"""
    conn = get_connection()
    users = conn.execute("""
        SELECT * FROM users 
        ORDER BY last_message_at DESC
    """).fetchall()
    conn.close()
    
    # Convert Row objects to dicts
    return [dict(user) for user in users]

def toggle_user_active(user_id):
    """Schaltet den aktiven Status eines Users um"""
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE users SET is_active = NOT is_active WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()

def is_user_active(user_id):
    """Prüft ob ein User aktiv ist"""
    user = get_user(user_id)
    if user:
        return bool(user['is_active'])
    return True

def toggle_human_mode(user_id):
    """Schaltet den Human Mode um"""
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE users SET human_mode = NOT human_mode WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()

def is_human_mode_on(user_id):
    """Prüft ob Human Mode aktiv ist"""
    user = get_user(user_id)
    if user:
        return bool(user['human_mode'])
    return False

def update_quiet_hours(user_id, start, end):
    """Aktualisiert die Nachtruhe-Zeiten"""
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE users SET quiet_start = ?, quiet_end = ? WHERE id = ?", (start, end, user_id))
    conn.commit()
    conn.close()

# ==================== MESSAGES ====================

def save_message(user_id, role, content):
    """Speichert eine Nachricht"""
    conn = get_connection()
    c = conn.cursor()
    now = datetime.datetime.now()
    c.execute("""
        INSERT INTO messages (user_id, role, content, timestamp) 
        VALUES (?, ?, ?, ?)
    """, (user_id, role, content, now))
    conn.commit()
    conn.close()

def get_chat_history(user_id, limit=50):
    """Holt den Chat-Verlauf"""
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT role, content, timestamp 
        FROM messages 
        WHERE user_id = ? 
        ORDER BY id DESC 
        LIMIT ?
    """, (user_id, limit))
    rows = c.fetchall()
    conn.close()
    
    history = [{
        "role": row["role"], 
        "content": row["content"], 
        "timestamp": row["timestamp"]
    } for row in rows]
    
    return history[::-1]  # Chronologisch sortieren

def get_full_chat(user_id):
    """Holt alle Nachrichten eines Users"""
    conn = get_connection()
    messages = conn.execute("""
        SELECT * FROM messages 
        WHERE user_id = ? 
        ORDER BY timestamp ASC
    """, (user_id,)).fetchall()
    conn.close()
    return messages

# ==================== FACTS & META ====================

def add_fact(user_id, key, value, fact_type="fact"):
    """Speichert ein Faktum mit Typ und Timestamp"""
    conn = get_connection()
    c = conn.cursor()
    now = datetime.datetime.now()
    c.execute("""
        INSERT OR REPLACE INTO user_facts (user_id, fact_key, fact_value, fact_type, updated_at) 
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, key, value, fact_type, now))
    conn.commit()
    conn.close()

def get_fact_value(user_id, key):
    """Holt einen einzelnen Fakt"""
    conn = get_connection()
    row = conn.execute("""
        SELECT fact_value 
        FROM user_facts 
        WHERE user_id = ? AND fact_key = ?
    """, (user_id, key)).fetchone()
    conn.close()
    
    if row:
        return row['fact_value']
    return None

def get_user_facts(user_id):
    """
    Holt alle Fakten eines Users strukturiert nach Typ
    Returns: { 'facts': {}, 'meta': {}, 'score': {}, ... }
    """
    conn = get_connection()
    rows = conn.execute("""
        SELECT fact_key, fact_value, fact_type, updated_at 
        FROM user_facts 
        WHERE user_id = ?
        ORDER BY updated_at DESC
    """, (user_id,)).fetchall()
    conn.close()
    
    result = {}
    
    for row in rows:
        ftype = row['fact_type']
        if ftype not in result:
            result[ftype] = {}
        
        # Versuche JSON zu parsen (für komplexe Daten)
        try:
            value = json.loads(row['fact_value'])
        except:
            value = row['fact_value']
        
        result[ftype][row['fact_key']] = value
    
    return result

# ==================== CONTACTS ====================

def add_contact(user_id, name, relationship, info="", potential="unbekannt"):
    """Fügt einen Kontakt/Verwandten hinzu"""
    conn = get_connection()
    c = conn.cursor()
    now = datetime.datetime.now()
    c.execute("""
        INSERT INTO user_contacts (user_id, name, relationship, info, potential, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, name, relationship, info, potential, now))
    conn.commit()
    conn.close()

def get_contacts(user_id):
    """Holt alle Kontakte eines Users"""
    conn = get_connection()
    contacts = conn.execute("""
        SELECT * FROM user_contacts 
        WHERE user_id = ?
        ORDER BY created_at DESC
    """, (user_id,)).fetchall()
    conn.close()
    
    return [{
        'name': c['name'],
        'relationship': c['relationship'],
        'info': c['info'],
        'potential': c['potential']
    } for c in contacts]

# ==================== LEAD SIGNALS ====================

def add_lead_signal(user_id, signal, category="general"):
    """Fügt ein Lead Signal hinzu"""
    conn = get_connection()
    c = conn.cursor()
    now = datetime.datetime.now()
    c.execute("""
        INSERT INTO lead_signals (user_id, signal, category, timestamp)
        VALUES (?, ?, ?, ?)
    """, (user_id, signal, category, now))
    conn.commit()
    conn.close()

def get_lead_signals(user_id, limit=20):
    """Holt die Lead Signals eines Users"""
    conn = get_connection()
    signals = conn.execute("""
        SELECT signal, category, timestamp 
        FROM lead_signals 
        WHERE user_id = ?
        ORDER BY timestamp DESC
        LIMIT ?
    """, (user_id, limit)).fetchall()
    conn.close()
    
    return [{
        'signal': s['signal'],
        'category': s['category'],
        'timestamp': s['timestamp']
    } for s in signals]

# ==================== STATISTICS ====================

def get_user_stats(user_id):
    """Holt Statistiken über einen User"""
    conn = get_connection()
    
    # Nachrichtenanzahl
    msg_count = conn.execute("""
        SELECT COUNT(*) as count 
        FROM messages 
        WHERE user_id = ?
    """, (user_id,)).fetchone()['count']
    
    # Fakten-Anzahl
    facts_count = conn.execute("""
        SELECT COUNT(*) as count 
        FROM user_facts 
        WHERE user_id = ?
    """, (user_id,)).fetchone()['count']
    
    # Kontakte-Anzahl
    contacts_count = conn.execute("""
        SELECT COUNT(*) as count 
        FROM user_contacts 
        WHERE user_id = ?
    """, (user_id,)).fetchone()['count']
    
    conn.close()
    
    return {
        'messages': msg_count,
        'facts': facts_count,
        'contacts': contacts_count
    }