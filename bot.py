import telebot
from telebot import types
import json, os, random
from flask import Flask
from threading import Thread

# ================= НАСТРОЙКИ =================

TOKEN = "8275742360:AAFDN-FBvQtgdTNeCOd9nlWXJFXQS_4LbaU"
ADMIN_IDS = [5333130126]  # твой Telegram ID
NEWS_CHANNEL = "@GramHubNews"

USERS_FILE = "users.json"
SPONSORS_FILE = "sponsors.json"

bot = telebot.TeleBot(TOKEN)

# ================= UPTIMEROBOT =================

app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is alive", 200

def run_web():
    app.run(host="0.0.0.0", port=10000)

Thread(target=run_web).start()

# ================= БАЗА =================

def load_json(path, default):
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(default, f, ensure_ascii=False, indent=2)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

users_db = load_json(USERS_FILE, {"users": {}})
sponsors_db = load_json(SPONSORS_FILE, {"sponsors": []})

def get_user(uid, username):
    uid = str(uid)
    if uid not in users_db["users"]:
        users_db["users"][uid] = {
            "username": username,
            "balance": 0,
            "refs": 0,
            "inviter": None,
            "captcha": False
        }
        save_json(USERS_FILE, users_db)
    return users_db["users"][uid]

# ================= КАПЧА =================

captcha_answers = {}

def send_captcha(m):
    a, b = random.randint(1,5), random.randint(1,5)
    captcha_answers[m.from_user.id] = a + b
    bot.send_message(m.chat.id, f"🤖 Докажи, что ты не бот\n\nСколько будет {a} + {b}?")

@bot.message_handler(func=lambda m: m.from_user.id in captcha_answers)
def check_captcha(m):
    if not m.text.isdigit():
        return
    if int(m.text) == captcha_answers[m.from_user.id]:
        del captcha_answers[m.from_user.id]
        u = get_user(m.from_user.id, m.from_user.username)
        u["captcha"] = True
        save_json(USERS_FILE, users_db)
        send_welcome(m)
    else:
        send_captcha(m)

# ================= ПОДПИСКА =================

def is_subscribed(uid):
    channels = [NEWS_CHANNEL] + sponsors_db["sponsors"]
    for ch in channels:
        try:
            member = bot.get_chat_member(ch, uid)
            if member.status not in ["member", "administrator", "creator"]:
                return False
        except:
            return False
    return True

# ================= КЛАВИАТУРЫ =================

def main_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("👤 Профиль", "👥 Пригласить")
    kb.add("💸 Вывод Gram")
    return kb

def admin_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("➕ Добавить спонсора", "➖ Удалить спонсора")
    kb.add("📢 Рассылка")
    kb.add("⬅️ Главное меню")
    return kb

def sponsors_kb():
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("📰 Новостник GramHub", url=f"https://t.me/{NEWS_CHANNEL[1:]}"))
    for s in sponsors_db["sponsors"]:
        kb.add(types.InlineKeyboardButton("💎 СПОНСОР", url=f"https://t.me/{s[1:]}"))
    kb.add(types.InlineKeyboardButton("✅ Проверить", callback_data="check"))
    return kb

# ================= START =================

@bot.message_handler(commands=["start"])
def start(m):
    u = get_user(m.from_user.id, m.from_user.username)

    if not u["captcha"]:
        send_captcha(m)
        return

    send_welcome(m)

def send_welcome(m):
    text = (
        f"Привет {m.from_user.username or m.from_user.first_name}!\n"
        "Ты попал в лучшего бота по заработку Gram 💎\n"
        "Приглашай друзей по реферальной ссылке и зарабатывай Gram!\n\n"
        "❝ Для начала подпишись на все каналы ниже 👇 ❞"
    )
    bot.send_message(m.chat.id, text, reply_markup=sponsors_kb())

# ================= CALLBACK =================

@bot.callback_query_handler(func=lambda c: c.data == "check")
def check(c):
    if not is_subscribed(c.from_user.id):
        bot.answer_callback_query(c.id, "❌ Подпишись на все каналы", show_alert=True)
        return

    bot.send_message(c.message.chat.id, "✅ Подписка подтверждена!", reply_markup=main_menu())

    if c.from_user.id in ADMIN_IDS:
        bot.send_message(c.message.chat.id, "⚙️ Админка", reply_markup=admin_menu())

# ================= МЕНЮ =================

@bot.message_handler(func=lambda m: m.text == "👤 Профиль")
def profile(m):
    u = get_user(m.from_user.id, m.from_user.username)
    bot.send_message(
        m.chat.id,
        f"👤 Профиль {m.from_user.username}\n\n"
        f"ID: {m.from_user.id}\n"
        f"Рефералы: {u['refs']}\n"
        f"Баланс Gram: {u['balance']}"
    )

@bot.message_handler(func=lambda m: m.text == "👥 Пригласить")
def invite(m):
    bot.send_message(
        m.chat.id,
        f"Привет {m.from_user.username}!\n"
        "Приглашай друзей и зарабатывай Gram.\n"
        "За одного реферала ты получишь 1250 Gram.\n\n"
        "❝ Реферал считается после подписки на всех спонсоров ❞\n\n"
        f"Твоя ссылка:\nhttps://t.me/{bot.get_me().username}?start={m.from_user.id}"
    )

@bot.message_handler(func=lambda m: m.text == "💸 Вывод Gram")
def withdraw(m):
    u = get_user(m.from_user.id, m.from_user.username)
    if u["balance"] < 20000:
        bot.send_message(m.chat.id, "❌ Минимальный вывод 20000 Gram")
        return
    bot.send_message(
        m.chat.id,
        "Для вывода Gram зайди в группу:\n"
        "https://t.me/+5yNBdXSxMoMzMzVi\n\n"
        "Ожидай вывод в течение 24 часов."
    )

# ================= АДМИН =================

@bot.message_handler(func=lambda m: m.text == "⬅️ Главное меню" and m.from_user.id in ADMIN_IDS)
def back(m):
    bot.send_message(m.chat.id, "Главное меню", reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text == "➕ Добавить спонсора" and m.from_user.id in ADMIN_IDS)
def add_s(m):
    msg = bot.send_message(m.chat.id, "Отправь @юзер канала")
    bot.register_next_step_handler(msg, save_s)

def save_s(m):
    if m.text.startswith("@"):
        sponsors_db["sponsors"].append(m.text)
        save_json(SPONSORS_FILE, sponsors_db)
        bot.send_message(m.chat.id, "✅ Спонсор добавлен")

@bot.message_handler(func=lambda m: m.text == "➖ Удалить спонсора" and m.from_user.id in ADMIN_IDS)
def del_s(m):
    msg = bot.send_message(m.chat.id, "Отправь @юзер канала")
    bot.register_next_step_handler(msg, remove_s)

def remove_s(m):
    if m.text in sponsors_db["sponsors"]:
        sponsors_db["sponsors"].remove(m.text)
        save_json(SPONSORS_FILE, sponsors_db)
        bot.send_message(m.chat.id, "✅ Спонсор удалён")

@bot.message_handler(func=lambda m: m.text == "📢 Рассылка" and m.from_user.id in ADMIN_IDS)
def mailing(m):
    msg = bot.send_message(m.chat.id, "Отправь текст для рассылки")
    bot.register_next_step_handler(msg, send_mail)

def send_mail(m):
    for uid in users_db["users"]:
        try:
            bot.send_message(uid, m.text)
        except:
            pass
    bot.send_message(m.chat.id, "✅ Рассылка завершена")

# ================= START BOT =================

print("Bot started")
bot.infinity_polling()
