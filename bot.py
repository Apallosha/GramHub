import telebot
from telebot import types
from flask import Flask, request
import json
import os
import time

# ================== НАСТРОЙКИ ==================

TOKEN = "8275742360:AAFDN-FBvQtgdTNeCOd9nlWXJFXQS_4LbaU"
ADMIN_IDS = [5333130126]  # ← твой Telegram ID
WEBHOOK_URL = "https://gramhub-2qn6.onrender.com"

USERS_FILE = "users.json"
SPONSORS_FILE = "sponsors.json"

bot = telebot.TeleBot(TOKEN, threaded=False)
app = Flask(__name__)

# ================== JSON ==================

def load_json(path, default):
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(default, f, ensure_ascii=False, indent=2)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ================== UTILS ==================

def is_admin(uid):
    return uid in ADMIN_IDS

def get_user(uid, username):
    db = load_json(USERS_FILE, {"users": {}})
    users = db["users"]

    if str(uid) not in users:
        users[str(uid)] = {
            "id": uid,
            "username": username,
            "grams": 0,
            "referrals": 0,
            "joined": int(time.time()),
            "last_check": 0
        }
        save_json(USERS_FILE, db)

    return users[str(uid)]

# ================== MENUS ==================

def main_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("👤 Профиль", "👥 Пригласить")
    kb.add("💸 Вывод Gram")
    return kb

def admin_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("➕ Добавить спонсора", "➖ Удалить спонсора")
    kb.add("📢 Рассылка")
    kb.add("🏠 Главное меню")
    return kb

# ================== ПОДПИСКА ==================

def check_subscription(uid):
    data = load_json(SPONSORS_FILE, {"sponsors": []})

    for sponsor in data["sponsors"]:
        try:
            if sponsor.startswith("@"):
                chat = sponsor
            else:
                chat = sponsor

            member = bot.get_chat_member(chat, uid)
            if member.status not in ["member", "administrator", "creator"]:
                return False
        except:
            return False

    return True

# ================== START ==================

@bot.message_handler(commands=["start"])
def start(m):
    uid = m.from_user.id
    user = get_user(uid, m.from_user.username)

    if not check_subscription(uid):
        data = load_json(SPONSORS_FILE, {"sponsors": []})
        text = (
            "❗ Для использования бота необходимо подписаться на всех спонсоров:\n\n"
        )
        for s in data["sponsors"]:
            text += f"• {s}\n"

        bot.send_message(uid, text)
        return

    bot.send_message(
        uid,
        "Добро пожаловать!\n\n"
        "Здесь ты можешь зарабатывать Gram, приглашая пользователей и выполняя условия.\n\n"
        "Используй меню ниже 👇",
        reply_markup=admin_menu() if is_admin(uid) else main_menu()
    )

# ================== PROFILE ==================

@bot.message_handler(func=lambda m: m.text == "👤 Профиль")
def profile(m):
    user = get_user(m.from_user.id, m.from_user.username)

    text = (
        "👤 Твой профиль\n\n"
        f"🆔 ID: {user['id']}\n"
        f"💰 Gram: {user['grams']}\n"
        f"👥 Рефералы: {user['referrals']}\n"
    )
    bot.send_message(m.chat.id, text)

# ================== REF ==================

@bot.message_handler(func=lambda m: m.text == "👥 Пригласить")
def invite(m):
    link = f"https://t.me/{bot.get_me().username}?start={m.from_user.id}"

    bot.send_message(
        m.chat.id,
        "👥 Приглашай друзей и получай Gram\n\n"
        f"🔗 Твоя ссылка:\n{link}"
    )

# ================== WITHDRAW ==================

@bot.message_handler(func=lambda m: m.text == "💸 Вывод Gram")
def withdraw(m):
    user = get_user(m.from_user.id, m.from_user.username)

    bot.send_message(
        m.chat.id,
        "💸 Вывод Gram\n\n"
        f"На балансе: {user['grams']} Gram\n\n"
        "Для вывода свяжись с администратором."
    )

# ================== ADMIN ==================

@bot.message_handler(commands=["admin"])
def admin(m):
    if not is_admin(m.from_user.id):
        return
    bot.send_message(m.chat.id, "⚙️ Админ-панель", reply_markup=admin_menu())

# ---- ADD SPONSOR ----

@bot.message_handler(func=lambda m: m.text == "➕ Добавить спонсора")
def add_sponsor(m):
    if not is_admin(m.from_user.id):
        return
    bot.send_message(m.chat.id, "Отправь @канал или invite-ссылку")
    bot.register_next_step_handler(m, save_sponsor)

def save_sponsor(m):
    data = load_json(SPONSORS_FILE, {"sponsors": []})
    s = m.text.strip()

    if s not in data["sponsors"]:
        data["sponsors"].append(s)
        save_json(SPONSORS_FILE, data)

    bot.send_message(m.chat.id, "✅ Спонсор добавлен", reply_markup=admin_menu())

# ---- REMOVE SPONSOR ----

@bot.message_handler(func=lambda m: m.text == "➖ Удалить спонсора")
def remove_sponsor(m):
    data = load_json(SPONSORS_FILE, {"sponsors": []})
    text = "Выбери номер:\n\n"

    for i, s in enumerate(data["sponsors"], 1):
        text += f"{i}. {s}\n"

    bot.send_message(m.chat.id, text)
    bot.register_next_step_handler(m, confirm_remove)

def confirm_remove(m):
    data = load_json(SPONSORS_FILE, {"sponsors": []})
    idx = int(m.text) - 1

    removed = data["sponsors"].pop(idx)
    save_json(SPONSORS_FILE, data)

    bot.send_message(
        m.chat.id,
        f"🗑 Удалено:\n{removed}",
        reply_markup=admin_menu()
    )

# ---- BROADCAST ----

@bot.message_handler(func=lambda m: m.text == "📢 Рассылка")
def broadcast(m):
    bot.send_message(m.chat.id, "Отправь сообщение для рассылки")
    bot.register_next_step_handler(m, send_broadcast)

def send_broadcast(m):
    users = load_json(USERS_FILE, {"users": {}})["users"]
    sent = 0

    for uid in users:
        try:
            bot.send_message(uid, m.text)
            sent += 1
        except:
            pass

    bot.send_message(m.chat.id, f"📬 Отправлено: {sent}", reply_markup=admin_menu())

# ================== FLASK ==================

@app.route("/", methods=["GET"])
def index():
    return "OK", 200

@app.route("/webhook", methods=["POST"])
def webhook():
    update = telebot.types.Update.de_json(
        request.stream.read().decode("utf-8")
    )
    bot.process_new_updates([update])
    return "OK", 200

# ================== START ==================

if __name__ == "__main__":
    bot.remove_webhook()
    bot.set_webhook(url=f"{WEBHOOK_URL}/webhook")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
