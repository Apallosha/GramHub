import telebot
from telebot import types
from flask import Flask, request
import json, os, random

# ================= НАСТРОЙКИ =================

TOKEN = "8275742360:AAFDN-FBvQtgdTNeCOd9nlWXJFXQS_4LbaU"
ADMIN_IDS = [5333130126]

NEWS_CHANNEL = "@GramHubNews"

WEBHOOK_PATH = f"/webhook/{TOKEN}"
WEBHOOK_URL = f"https://gramhub-2qn6.onrender.com{WEBHOOK_PATH}"

USERS_FILE = "users.json"
SPONSORS_FILE = "sponsors.json"

REF_REWARD = 1250
MIN_WITHDRAW = 25000

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# ================= УТИЛИТЫ =================

def load_json(path, default):
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(default, f, ensure_ascii=False, indent=2)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_user(uid, username):
    db = load_json(USERS_FILE, {"users": {}})
    if str(uid) not in db["users"]:
        db["users"][str(uid)] = {
            "id": uid,
            "username": username,
            "balance": 0,
            "refs": [],
            "invited_by": None,
            "subscribed_once": False
        }
        save_json(USERS_FILE, db)
    return db["users"][str(uid)]

def get_chat_id_from_invite(link):
    try:
        chat = bot.get_chat(link)
        return chat.id
    except:
        return None

def is_subscribed(user_id):
    sponsors = load_json(SPONSORS_FILE, {"sponsors": []})["sponsors"]

    for s in sponsors:
        try:
            if s.startswith("@"):
                chat_id = s
            elif s.startswith("https://t.me/"):
                chat_id = get_chat_id_from_invite(s)
                if not chat_id:
                    return False
            else:
                return False

            member = bot.get_chat_member(chat_id, user_id)
            if member.status in ["left", "kicked"]:
                return False
        except:
            return False
    return True

# ================= КЛАВИАТУРЫ =================

def main_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("👤 Профиль", "📨 Пригласить")
    kb.add("💸 Вывод Gram")
    return kb

def admin_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("➕ Добавить спонсора", "➖ Удалить спонсора")
    kb.add("📢 Рассылка", "🏠 Главное меню")
    return kb

# ================= START + КАПЧА =================

@bot.message_handler(commands=["start"])
def start(m):
    user = get_user(m.from_user.id, m.from_user.username)
    a, b = random.randint(1,5), random.randint(1,5)
    bot.send_message(
        m.chat.id,
        f"🤖 Капча: {a} + {b} = ?",
    )
    bot.register_next_step_handler(m, check_captcha, a+b)

def check_captcha(m, answer):
    if m.text != str(answer):
        bot.send_message(m.chat.id, "❌ Неверно, попробуй снова /start")
        return

    sponsors = load_json(SPONSORS_FILE, {"sponsors": []})["sponsors"]

    text = (
        f"Привет {m.from_user.username}!\n"
        "Ты попал в лучшего бота по заработку Gram,\n"
        "приглашай друзей по реферальной ссылке и зарабатывай Gram!\n\n"
        "Для начала подпишись на все каналы ниже 👇"
    )

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("📰 Новостник GramHub", url=f"https://t.me/{NEWS_CHANNEL.replace('@','')}"))

    for s in sponsors:
        kb.add(types.InlineKeyboardButton("СПОНСОР", url=s))

    kb.add(types.InlineKeyboardButton("✅ Проверить", callback_data="check_sub"))

    bot.send_message(m.chat.id, text, reply_markup=kb)

# ================= ПРОВЕРКА ПОДПИСКИ =================

@bot.callback_query_handler(func=lambda c: c.data == "check_sub")
def check_sub(c):
    if not is_subscribed(c.from_user.id):
        bot.answer_callback_query(c.id, "❌ Подпишись на все каналы")
        return

    db = load_json(USERS_FILE, {"users": {}})
    user = db["users"][str(c.from_user.id)]
    user["subscribed_once"] = True
    save_json(USERS_FILE, db)

    bot.send_message(c.message.chat.id, "✅ Подписка подтверждена", reply_markup=main_menu())

# ================= ПРОФИЛЬ =================

@bot.message_handler(func=lambda m: m.text == "👤 Профиль")
def profile(m):
    if not is_subscribed(m.from_user.id):
        bot.send_message(m.chat.id, "❌ Ты отписался от спонсоров")
        return

    user = get_user(m.from_user.id, m.from_user.username)
    text = (
        f"Профиль {m.from_user.username}\n\n"
        f"ID: {user['id']}\n"
        f"Рефералы: {len(user['refs'])}\n"
        f"Баланс Gram: {user['balance']}"
    )
    bot.send_message(m.chat.id, text)

# ================= ПРИГЛАСИТЬ =================

@bot.message_handler(func=lambda m: m.text == "📨 Пригласить")
def invite(m):
    if not is_subscribed(m.from_user.id):
        bot.send_message(m.chat.id, "❌ Ты отписался от спонсоров")
        return

    link = f"https://t.me/{bot.get_me().username}?start={m.from_user.id}"
    text = (
        f"Привет {m.from_user.username}! Приглашай друзей и зарабатывай Gram,\n"
        f"за одного реферала ты получишь 1250 Gram!\n\n"
        f"реферал считается после подписки на всех спонсоров!\n\n"
        f"Твоя ссылка: {link}"
    )
    bot.send_message(m.chat.id, text)

# ================= ВЫВОД =================

@bot.message_handler(func=lambda m: m.text == "💸 Вывод Gram")
def withdraw(m):
    if not is_subscribed(m.from_user.id):
        bot.send_message(m.chat.id, "❌ Ты отписался от спонсоров")
        return

    user = get_user(m.from_user.id, m.from_user.username)
    if user["balance"] < MIN_WITHDRAW:
        bot.send_message(m.chat.id, "Минимальный вывод 20000 Gram")
        return

    bot.send_message(m.chat.id, "Введи сумму для вывода (минимум 20000)")
    bot.register_next_step_handler(m, process_withdraw)

def process_withdraw(m):
    try:
        amount = int(m.text)
    except:
        return

    db = load_json(USERS_FILE, {"users": {}})
    user = db["users"][str(m.from_user.id)]

    if amount < MIN_WITHDRAW or user["balance"] < amount:
        bot.send_message(m.chat.id, "Недостаточно Gram для вывода!")
        return

    user["balance"] -= amount
    save_json(USERS_FILE, db)

    bot.send_message(
        m.chat.id,
        "Дальше для вывода Gram зайди в группу\n"
        "https://t.me/+5yNBdXSxMoMzMzVi\n"
        "и ожидай вывода в течении 24 часов!"
    )

# ================= АДМИНКА =================

@bot.message_handler(commands=["admin"])
def admin(m):
    if m.from_user.id in ADMIN_IDS:
        bot.send_message(m.chat.id, "Админ панель", reply_markup=admin_menu())

# ================= WEBHOOK =================

@app.route(WEBHOOK_PATH, methods=["POST"])
def webhook():
    update = telebot.types.Update.de_json(
        request.stream.read().decode("utf-8")
    )
    bot.process_new_updates([update])
    return "OK", 200

@app.route("/")
def index():
    return "Bot is alive", 200

if __name__ == "__main__":
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL)
    app.run(host="0.0.0.0", port=10000)
