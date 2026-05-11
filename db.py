import sqlite3
import os
import bcrypt

DB_PATH = "database/tracker.db"
DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "admin123"
DEFAULT_ADMIN_ROLE = "admin"
DEFAULT_FEATURES = [
    "E-Invoice",
    "KYC Aadhaar",
    "KYC Bank",
    "SMS Integration",
    "WhatsApp Integration",
    "Bank Integration"
]

def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    os.makedirs("database", exist_ok=True)

    conn = get_connection()
    cur = conn.cursor()

    # ================= CLIENTS =================
    cur.execute("""
    CREATE TABLE IF NOT EXISTS clients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        manpower INTEGER,
        state TEXT,
        po_date TEXT,
        mail_date TEXT,
        owner TEXT,
        product TEXT,
        version TEXT,
        status TEXT DEFAULT 'New',
        client_code TEXT UNIQUE
    )
    """)

    # Ensure old manual client_id field is removed and client_code exists
    cols = [row[1] for row in cur.execute("PRAGMA table_info(clients)").fetchall()]
    if "client_id" in cols:
        try:
            cur.execute("ALTER TABLE clients DROP COLUMN client_id")
        except sqlite3.OperationalError:
            pass

    if "client_code" not in cols:
        cur.execute("ALTER TABLE clients ADD COLUMN client_code TEXT UNIQUE")

    for rid, code in cur.execute("SELECT id, client_code FROM clients").fetchall():
        if not code:
            cur.execute(
                "UPDATE clients SET client_code=? WHERE id=?",
                (f"CLD{rid:04d}", rid)
            )

    # ================= CONTACTS =================
    cur.execute("""
    CREATE TABLE IF NOT EXISTS client_contacts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER,
        name TEXT,
        designation TEXT,
        email TEXT,
        phone TEXT
    )
    """)

    # ================= FEATURES =================
    cur.execute("""
    CREATE TABLE IF NOT EXISTS client_features (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER,
        feature_name TEXT,
        enabled INTEGER DEFAULT 0,
        enabled_on TEXT
    )
    """)

    # ================= UPDATES (TIMELINE) =================
    cur.execute("""
    CREATE TABLE IF NOT EXISTS updates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER,
        parent_id INTEGER,
        type TEXT,  -- update / mom / mom_point / requirement / feature_log
        title TEXT,
        description TEXT,
        status TEXT,
        is_paid INTEGER DEFAULT 0,
                
        created_at TEXT,
        closed_at TEXT,
                
        created_by TEXT,
                
        remarks TEXT
    )
    """)

    # ================= USERS =================
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT
    )
    """)

    # ================= FEATURES MASTER =================
    cur.execute("""
    CREATE TABLE IF NOT EXISTS features_master (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        feature_name TEXT UNIQUE
    )
    """)

    # ================= DEFAULT FEATURES =================
    for feature in DEFAULT_FEATURES:
        cur.execute("SELECT 1 FROM features_master WHERE feature_name=?", (feature,))
        if not cur.fetchone():
            cur.execute("INSERT INTO features_master (feature_name) VALUES (?)", (feature,))

    # ================= DEFAULT ADMIN USER =================
    cur.execute("SELECT 1 FROM users WHERE username=?", (DEFAULT_ADMIN_USERNAME,))
    if not cur.fetchone():
        hashed = bcrypt.hashpw(DEFAULT_ADMIN_PASSWORD.encode(), bcrypt.gensalt()).decode()
        cur.execute("""
        INSERT INTO users (username, password, role)
        VALUES (?, ?, ?)
        """, (DEFAULT_ADMIN_USERNAME, hashed, DEFAULT_ADMIN_ROLE))

    conn.commit()
    conn.close()