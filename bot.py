import telebot
from telebot import types
import json, os, random
from flask import Flask, request

# ================= НАСТРОЙКИ =================

TOKEN = "8275742360:AAFDN-FBvQtgdTNeCOd9nlWXJFXQS_4LbaU"
ADMIN_IDS = [5333130126]

WEBHOOK_PATH = f"/webhook/{TOKEN}"
WEBHOOK_URL = f"https://gramhub-2qn6.onrender.com{WEBHOOK_PATH}"

USERS_FILE = "users.json"
SPONSORS_FILE = "sponsors.json"

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

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
withdraw_wait = set()

def send_captcha(m):
    a, b = random.randint(1, 5), random.randint(1, 5)
    captcha_answers[m.from_user.id] = a + b
    bot.send_message(
        m.chat.id,
        f"🤖 Докажи, что ты не бот!\n\nСколько будет {a} + {b}?"
    )

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

# ================= ПРОВЕРКА ПОДПИСКИ =================

def is_subscribed(uid):
    for s in sponsors_db["sponsors"]:
        if s["type"] == "public":
            try:
                member = bot.get_chat_member(s["value"], uid)
                if member.status not in ["member", "administrator", "creator"]:
                    return False
            except:
                return False
        elif s["type"] == "private":
            continue
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
    for s in sponsors_db["sponsors"]:
        if s["type"] == "public":
            kb.add(types.InlineKeyboardButton(
                "📢 Канал",
                url=f"https://t.me/{s['value'][1:]}"
            ))
        elif s["type"] == "private":
            kb.add(types.InlineKeyboardButton(
                "🔒 Приват канал",
                url=s["value"]
            ))
    kb.add(types.InlineKeyboardButton("✅ Проверить", callback_data="check_subs"))
    return kb

# ================= START + РЕФЕРАЛ =================

@bot.message_handler(commands=["start"])
def start(m):
    args = m.text.split()
    u = get_user(m.from_user.id, m.from_user.username)

    if len(args) > 1 and u["inviter"] is None:
        inviter_id = args[1]
        if inviter_id != str(m.from_user.id) and inviter_id in users_db["users"]:
            u["inviter"] = inviter_id
            users_db["users"][inviter_id]["refs"] += 1
            users_db["users"][inviter_id]["balance"] += 1250
            save_json(USERS_FILE, users_db)
            try:
                bot.send_message(inviter_id, "У вас новый реферал ☘️")
            except:
                pass

    if not u["captcha"]:
        send_captcha(m)
        return

    send_welcome(m)

def send_welcome(m):
    text = (
        f"Привет {m.from_user.username or m.from_user.first_name}!\n\n"
        "Ты попал в лучшего бота по заработку Gram, "
        "приглашай друзей по реферальной ссылке и зарабатывай Gram!\n\n"
        "❝ Для начала подпишись на все каналы ниже 👇 ❞"
    )
    bot.send_message(m.chat.id, text, reply_markup=sponsors_kb())

# ================= CALLBACK =================

@bot.callback_query_handler(func=lambda c: c.data == "check_subs")
def check_subs(c):
    if not is_subscribed(c.from_user.id):
        bot.answer_callback_query(
            c.id,
            "❌ Ты подписался не на все каналы!",
            show_alert=True
        )
        return

    bot.send_message(
        c.message.chat.id,
        "✅ Подписка подтверждена!",
        reply_markup=main_menu()
    )

# ================= МЕНЮ =================

@bot.message_handler(func=lambda m: m.text == "👤 Профиль")
def profile(m):
    u = get_user(m.from_user.id, m.from_user.username)
    bot.send_message(
        m.chat.id,
        f"Профиль {m.from_user.username}\n\n"
        f"ID: {m.from_user.id}\n"
        f"Рефералы: {u['refs']}\n"
        f"Баланс Gram: {u['balance']}"
    )

@bot.message_handler(func=lambda m: m.text == "👥 Пригласить")
def invite(m):
    bot.send_message(
        m.chat.id,
        f"Привет {m.from_user.username}!\n\n"
        "Приглашай друзей и зарабатывай Gram, "
        "за одного реферала ты получишь 1250 Gram!\n\n"
        "❝ Реферал считается после подписки на всех спонсоров! ❞\n\n"
        f"Твоя ссылка:\nhttps://t.me/{bot.get_me().username}?start={m.from_user.id}"
    )

@bot.message_handler(func=lambda m: m.text == "💸 Вывод Gram")
def withdraw(m):
    u = get_user(m.from_user.id, m.from_user.username)

    if u["balance"] < 25000:
        bot.send_message(m.chat.id, "Минимальный вывод 25000 Gram")
        return

    withdraw_wait.add(m.from_user.id)
    bot.send_message(
        m.chat.id,
        "💸 Введите сумму для вывода\n\n"
        "Минимум: 25000 Gram\n"
        f"Ваш баланс: {u['balance']} Gram"
    )

@bot.message_handler(func=lambda m: m.from_user.id in withdraw_wait)
def process_withdraw(m):
    if not m.text.isdigit():
        return

    amount = int(m.text)
    u = get_user(m.from_user.id, m.from_user.username)

    if amount < 25000:
        bot.send_message(m.chat.id, "❌ Минимальный вывод 25000 Gram")
        return

    if amount > u["balance"]:
        bot.send_message(m.chat.id, "❌ Недостаточно средств на балансе")
        return

    u["balance"] -= amount
    save_json(USERS_FILE, users_db)
    withdraw_wait.remove(m.from_user.id)

    bot.send_message(
        m.chat.id,
        "✅ Gram успешно списаны!\n\n"
        "Для получения Gram зайди в группу:\n"
        "https://t.me/+5yNBdXSxMoMzMzVi\n\n"
        "⏳ Ожидай вывод в течение 24 часов!"
    )

# ================= АДМИН =================

@bot.message_handler(commands=["admin"])
def admin_cmd(m):
    if m.from_user.id not in ADMIN_IDS:
        return
    bot.send_message(m.chat.id, "⚙️ Админ панель", reply_markup=admin_menu())

@bot.message_handler(func=lambda m: m.text == "⬅️ Главное меню" and m.from_user.id in ADMIN_IDS)
def admin_back(m):
    bot.send_message(m.chat.id, "Главное меню", reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text == "➕ Добавить спонсора" and m.from_user.id in ADMIN_IDS)
def add_sponsor(m):
    msg = bot.send_message(
        m.chat.id,
        "Отправь @юзер канала ИЛИ invite-ссылку приватного канала"
    )
    bot.register_next_step_handler(msg, save_sponsor)

def save_sponsor(m):
    text = m.text.strip()
    if text.startswith("@"):
        sponsors_db["sponsors"].append({"type": "public", "value": text})
    elif text.startswith("https://t.me/+"):
        sponsors_db["sponsors"].append({"type": "private", "value": text})
    else:
        bot.send_message(m.chat.id, "❌ Неверный формат")
        return
    save_json(SPONSORS_FILE, sponsors_db)
    bot.send_message(m.chat.id, "✅ Спонсор добавлен")

@bot.message_handler(func=lambda m: m.text == "➖ Удалить спонсора" and m.from_user.id in ADMIN_IDS)
def del_sponsor(m):
    msg = bot.send_message(m.chat.id, "Отправь @юзер или invite-ссылку")
    bot.register_next_step_handler(msg, remove_sponsor)

def remove_sponsor(m):
    for s in sponsors_db["sponsors"]:
        if s["value"] == m.text.strip():
            sponsors_db["sponsors"].remove(s)
            save_json(SPONSORS_FILE, sponsors_db)
            bot.send_message(m.chat.id, "✅ Спонсор удалён")
            return
    bot.send_message(m.chat.id, "❌ Спонсор не найден")

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
