import telebot
from telebot import types
import json, os, random, threading
from flask import Flask

# ========= НАСТРОЙКИ =========
TOKEN = "8275742360:AAFDN-FBvQtgdTNeCOd9nlWXJFXQS_4LbaU"
ADMIN_IDS = [5333130126]
NEWS_CHANNEL = "@GramHubNews"
MIN_WITHDRAW = 20000
REF_BONUS = 1250
DB_FILE = "db.json"

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# ========= FLASK =========
app = Flask(__name__)
@app.route("/")
def index():
    return "OK"

threading.Thread(
    target=lambda: app.run(host="0.0.0.0", port=8080),
    daemon=True
).start()

# ========= БАЗА =========
def load_db():
    if not os.path.exists(DB_FILE):
        return {"users": {}, "sponsors": []}
    return json.load(open(DB_FILE, "r", encoding="utf-8"))

def save_db():
    json.dump(db, open(DB_FILE, "w", encoding="utf-8"),
              indent=2, ensure_ascii=False)

db = load_db()

# ========= УТИЛИТЫ =========
def get_user(uid, username):
    uid = str(uid)
    if uid not in db["users"]:
        db["users"][uid] = {
            "id": uid,
            "username": username,
            "balance": 0,
            "refs": 0,
            "ref_by": None,
            "last_msg": None
        }
        save_db()
    return db["users"][uid]

def delete_last(uid):
    u = db["users"].get(str(uid))
    if u and u["last_msg"]:
        try:
            bot.delete_message(uid, u["last_msg"])
        except:
            pass
        u["last_msg"] = None
        save_db()

def send(uid, text, **kwargs):
    delete_last(uid)
    msg = bot.send_message(uid, text, **kwargs)
    db["users"][str(uid)]["last_msg"] = msg.message_id
    save_db()
    return msg   # 🔥 ВАЖНО

def check_subs(uid):
    for ch in [NEWS_CHANNEL] + db["sponsors"]:
        try:
            if bot.get_chat_member(ch, uid).status in ["left", "kicked"]:
                return False
        except:
            return False
    return True

# ========= КАПЧА =========
captcha = {}

@bot.message_handler(commands=["start"])
def start(m):
    a, b = random.randint(1,5), random.randint(1,5)
    captcha[m.from_user.id] = a+b
    bot.send_message(m.chat.id, f"🤖 {a} + {b} = ?")

@bot.message_handler(func=lambda m: m.from_user.id in captcha)
def captcha_ok(m):
    if m.text.isdigit() and int(m.text) == captcha[m.from_user.id]:
        del captcha[m.from_user.id]
        welcome(m)

# ========= ПРИВЕТ =========
def welcome(m):
    uid = m.from_user.id
    get_user(uid, m.from_user.username)

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton(
        "📰 Новостник GramHub",
        url=f"https://t.me/{NEWS_CHANNEL[1:]}"
    ))
    for s in db["sponsors"]:
        kb.add(types.InlineKeyboardButton(
            "💎 СПОНСОР", url=f"https://t.me/{s[1:]}"
        ))
    kb.add(types.InlineKeyboardButton("✅ Проверить", callback_data="check"))

    send(uid,
         f"👋 Привет {m.from_user.first_name}\n\n"
         "<blockquote>Подпишись на все каналы 👇</blockquote>",
         reply_markup=kb)

# ========= ПРОВЕРКА =========
@bot.callback_query_handler(func=lambda c: c.data == "check")
def check(c):
    uid = c.from_user.id
    if not check_subs(uid):
        bot.answer_callback_query(c.id, "❌ Не все подписки", show_alert=True)
        return

    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("👤 Профиль", "📨 Пригласить")
    kb.add("💸 Вывод Gram")
    send(uid, "✅ Готово", reply_markup=kb)

# ========= ПРОФИЛЬ =========
@bot.message_handler(func=lambda m: m.text == "👤 Профиль")
def profile(m):
    u = db["users"][str(m.from_user.id)]
    send(m.chat.id,
         f"👤 Профиль\n\n"
         f"ID: {u['id']}\n"
         f"Рефы: {u['refs']}\n"
         f"Баланс: {u['balance']}")

# ========= ВЫВОД =========
@bot.message_handler(func=lambda m: m.text == "💸 Вывод Gram")
def withdraw(m):
    u = db["users"][str(m.from_user.id)]
    if u["balance"] < MIN_WITHDRAW:
        send(m.chat.id, f"❌ Мин. {MIN_WITHDRAW}")
        return
    msg = send(m.chat.id, "Введи сумму")
    bot.register_next_step_handler(msg, withdraw_done)

def withdraw_done(m):
    if not m.text.isdigit():
        return
    amt = int(m.text)
    u = db["users"][str(m.from_user.id)]
    if amt > u["balance"]:
        send(m.chat.id, "❌ Недостаточно")
        return
    u["balance"] -= amt
    save_db()
    send(m.chat.id, "✅ Заявка принята (до 24ч)")

# ========= АДМИНКА =========
@bot.message_handler(commands=["admin"])
def admin(m):
    if m.from_user.id not in ADMIN_IDS:
        return
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("➕ Добавить спонсора", "➖ Удалить спонсора")
    kb.add("💰 Начислить Gram", "💸 Списать Gram")
    kb.add("📢 Рассылка", "🏠 Главное меню")
    send(m.chat.id, "⚙️ Админка", reply_markup=kb)

# ---- СПОНСОРЫ ----
@bot.message_handler(func=lambda m: m.text == "➕ Добавить спонсора")
def add_s(m):
    msg = send(m.chat.id, "@username канала")
    bot.register_next_step_handler(msg, add_s_done)

def add_s_done(m):
    if m.text.startswith("@"):
        db["sponsors"].append(m.text)
        save_db()
        send(m.chat.id, "✅ Добавлен")

@bot.message_handler(func=lambda m: m.text == "➖ Удалить спонсора")
def del_s(m):
    msg = send(m.chat.id, "@username канала")
    bot.register_next_step_handler(msg, del_s_done)

def del_s_done(m):
    if m.text in db["sponsors"]:
        db["sponsors"].remove(m.text)
        save_db()
        send(m.chat.id, "❌ Удалён")

# ---- БАЛАНС ----
@bot.message_handler(func=lambda m: m.text == "💰 Начислить Gram")
def add_bal(m):
    msg = send(m.chat.id, "ID СУММА")
    bot.register_next_step_handler(msg, add_bal_done)

def add_bal_done(m):
    uid, amt = m.text.split()
    db["users"][uid]["balance"] += int(amt)
    save_db()
    send(m.chat.id, "✅ Начислено")

@bot.message_handler(func=lambda m: m.text == "💸 Списать Gram")
def rem_bal(m):
    msg = send(m.chat.id, "ID СУММА")
    bot.register_next_step_handler(msg, rem_bal_done)

def rem_bal_done(m):
    uid, amt = m.text.split()
    amt = int(amt)
    if db["users"][uid]["balance"] >= amt:
        db["users"][uid]["balance"] -= amt
        save_db()
        send(m.chat.id, "✅ Списано")

# ========= RUN =========
print("BOT STARTED")
bot.infinity_polling()
