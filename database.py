import sqlite3
import os

DB_FILE = "users.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # таблица пользователей
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        username TEXT,
        balance INTEGER DEFAULT 0,
        refs INTEGER DEFAULT 0,
        invited_by INTEGER,
        captcha INTEGER,
        sub_ok INTEGER DEFAULT 0
    )""")
    # таблица спонсоров
    c.execute("""CREATE TABLE IF NOT EXISTS sponsors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        link TEXT UNIQUE
    )""")
    conn.commit()
    conn.close()

def get_user(uid):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE id=?", (uid,))
    user = c.fetchone()
    if not user:
        c.execute("INSERT INTO users (id) VALUES (?)", (uid,))
        conn.commit()
        c.execute("SELECT * FROM users WHERE id=?", (uid,))
        user = c.fetchone()
    conn.close()
    return user

def update_user(uid, **kwargs):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    for key, value in kwargs.items():
        c.execute(f"UPDATE users SET {key}=? WHERE id=?", (value, uid))
    conn.commit()
    conn.close()

def get_all_users():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id FROM users")
    users = [x[0] for x in c.fetchall()]
    conn.close()
    return users

# =================== спонсоры ===================

def add_sponsor(link):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO sponsors (link) VALUES (?)", (link,))
    conn.commit()
    conn.close()

def remove_sponsor(link):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM sponsors WHERE link=?", (link,))
    conn.commit()
    conn.close()

def get_sponsors():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT link FROM sponsors")
    sponsors = [x[0] for x in c.fetchall()]
    conn.close()
    return sponsors
