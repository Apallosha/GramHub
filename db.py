import sqlite3

conn = sqlite3.connect("data.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    balance INTEGER DEFAULT 0,
    refs INTEGER DEFAULT 0,
    invited_by INTEGER
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS sponsors (
    link TEXT PRIMARY KEY
)
""")

conn.commit()

# ===== USERS =====
def add_user(uid, username, invited_by=None):
    cur.execute(
        "INSERT OR IGNORE INTO users (user_id, username, invited_by) VALUES (?,?,?)",
        (uid, username, invited_by)
    )
    conn.commit()

def get_user(uid):
    cur.execute("SELECT * FROM users WHERE user_id=?", (uid,))
    return cur.fetchone()

def add_balance(uid, amount):
    cur.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, uid))
    conn.commit()

def sub_balance(uid, amount):
    cur.execute("UPDATE users SET balance = balance - ? WHERE user_id=?", (amount, uid))
    conn.commit()

def add_ref(uid):
    cur.execute("UPDATE users SET refs = refs + 1 WHERE user_id=?", (uid,))
    conn.commit()

def all_users():
    cur.execute("SELECT user_id FROM users")
    return [i[0] for i in cur.fetchall()]

# ===== SPONSORS =====
def add_sponsor(link):
    cur.execute("INSERT OR IGNORE INTO sponsors VALUES (?)", (link,))
    conn.commit()

def del_sponsor(link):
    cur.execute("DELETE FROM sponsors WHERE link=?", (link,))
    conn.commit()

def get_sponsors():
    cur.execute("SELECT link FROM sponsors")
    return [i[0] for i in cur.fetchall()]
