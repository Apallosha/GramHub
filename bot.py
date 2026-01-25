import telebot
from telebot import types
import json, os, random
from flask import Flask, request

TOKEN = "8275742360:AAFDN-FBvQtgdTNeCOd9nlWXJFXQS_4LbaU"
ADMIN_IDS = [5333130126]
WEBHOOK_URL = "https://gramhub-2qn6.onrender.com"

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

USERS_FILE = "users.json"
SPONSORS_FILE = "sponsors.json"

# ================= БАЗА =================

def load_json(path, default):
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(default, f)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

users_db = load_json(USERS_FILE, {"users": {}})
sponsors_db = load_json(SPONSORS_FILE, {"sponsors": []})

def get_user(uid, username=None):
    uid = str(uid)
    if uid not in users_db["users"]:
        users_db["users"][uid] = {
            "username": username,
            "balance": 0,
            "refs": 0,
            "ref_by": None,
            "verified": False,
            "captcha": False,
            "captcha_answer": None
        }
        save_json(USERS_FILE, users_db)
    return users_db["users"][uid]

# ================= МЕНЮ =================

def main_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("👤 Профиль", "👥 Пригласить")
    kb.add("💸 Вывод Gram")
    return kb

def admin_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("➕ Начислить баланс", "➖ Списать баланс")
    kb.add("➕ Добавить спонсора", "➖ Удалить спонсора")
    kb.add("📢 Рассылка")
    kb.add("⬅️ Главное меню")
    return kb

# ================= КАПЧА =================

def send_captcha(chat_id, user):
    a = random.randint(1, 9)
    b = random.randint(1, 9)
    user["captcha_answer"] = a + b
    save_json(USERS_FILE, users_db)

    bot.send_message(
        chat_id,
        f"🔐 Подтвердите, что вы не бот:\n\n{a} + {b} = ?"
    )

@bot.message_handler(func=lambda m: not get_user(m.from_user.id).get("captcha"))
def captcha_check(m):
    user = get_user(m.from_user.id, m.from_user.username)

    if user["captcha_answer"] is None:
        send_captcha(m.chat.id, user)
        return

    if not m.text.isdigit() or int(m.text) != user["captcha_answer"]:
        bot.send_message(m.chat.id, "❌ Неверно, попробуй ещё раз")
        send_captcha(m.chat.id, user)
        return

    user["captcha"] = True
    user["captcha_answer"] = None
    save_json(USERS_FILE, users_db)

    bot.send_message(m.chat.id, "✅ Капча пройдена!")

# ================= ПРОВЕРКА СПОНСОРОВ =================

def check_subs(user_id):
    for s in sponsors_db["sponsors"]:
        if s.startswith("@"):
            try:
                member = bot.get_chat_member(s, user_id)
                if member.status == "left":
                    return False
            except:
                return False
    return True

# ================= START =================

@bot.message_handler(commands=["start"])
def start(m):
    user = get_user(m.from_user.id, m.from_user.username)

    if not user["captcha"]:
        send_captcha(m.chat.id, user)
        return

    if len(m.text.split()) > 1:
        ref = m.text.split()[1]
        if ref != str(m.from_user.id):
            user["ref_by"] = ref
            save_json(USERS_FILE, users_db)

    kb = types.InlineKeyboardMarkup()
    for s in sponsors_db["sponsors"]:
        kb.add(types.InlineKeyboardButton("🔔 СПОНСОР", url=s))
    kb.add(types.InlineKeyboardButton("✅ Проверить", callback_data="check"))

    bot.send_message(
        m.chat.id,
        "Чтобы пользоваться ботом 👇\nПодпишись на всех спонсоров",
        reply_markup=kb
    )

# ================= ПРОВЕРИТЬ =================

@bot.callback_query_handler(func=lambda c: c.data == "check")
def check(c):
    user = get_user(c.from_user.id, c.from_user.username)

    if not check_subs(c.from_user.id):
        bot.answer_callback_query(c.id, "❌ Вы не подписались на всех")
        return

    if not user["verified"]:
        user["verified"] = True

        if user["ref_by"]:
            ref = get_user(user["ref_by"])
            ref["balance"] += 1250
            ref["refs"] += 1
            save_json(USERS_FILE, users_db)

            try:
                bot.send_message(int(user["ref_by"]), "☘️ У вас новый реферал!")
            except:
                pass

    save_json(USERS_FILE, users_db)
    bot.send_message(c.message.chat.id, "✅ Доступ открыт!", reply_markup=main_menu())

# ================= ПРОФИЛЬ =================

@bot.message_handler(func=lambda m: m.text == "👤 Профиль")
def profile(m):
    u = get_user(m.from_user.id)
    bot.send_message(
        m.chat.id,
        f"👤 Профиль\n\n"
        f"ID: {m.from_user.id}\n"
        f"Рефералы: {u['refs']}\n"
        f"Баланс: {u['balance']} Gram"
    )

# ================= ВЫВОД =================

@bot.message_handler(func=lambda m: m.text == "💸 Вывод Gram")
def withdraw(m):
    u = get_user(m.from_user.id)
    if u["balance"] < 25000:
        bot.send_message(m.chat.id, "❌ Минимальный вывод 25000 Gram")
        return
    msg = bot.send_message(m.chat.id, "Введите сумму для вывода:")
    bot.register_next_step_handler(msg, withdraw_sum)

def withdraw_sum(m):
    u = get_user(m.from_user.id)
    if not m.text.isdigit():
        bot.send_message(m.chat.id, "Введите число")
        return

    amount = int(m.text)
    if amount < 25000 or amount > u["balance"]:
        bot.send_message(m.chat.id, "❌ Неверная сумма")
        return

    u["balance"] -= amount
    save_json(USERS_FILE, users_db)

    bot.send_message(
        m.chat.id,
        f"✅ Заявка на {amount} Gram принята\n"
        f"Ожидайте до 24 часов"
    )

# ================= АДМИН =================

@bot.message_handler(commands=["admin"])
def admin(m):
    if m.from_user.id in ADMIN_IDS:
        bot.send_message(m.chat.id, "⚙️ Админ панель", reply_markup=admin_menu())

@bot.message_handler(func=lambda m: m.text == "➕ Начислить баланс" and m.from_user.id in ADMIN_IDS)
def add_balance(m):
    msg = bot.send_message(m.chat.id, "Введите ID пользователя:")
    bot.register_next_step_handler(msg, add_balance_sum)

def add_balance_sum(m):
    uid = m.text
    msg = bot.send_message(m.chat.id, "Введите сумму:")
    bot.register_next_step_handler(msg, lambda x: change_balance(uid, x, True))

@bot.message_handler(func=lambda m: m.text == "➖ Списать баланс" and m.from_user.id in ADMIN_IDS)
def remove_balance(m):
    msg = bot.send_message(m.chat.id, "Введите ID пользователя:")
    bot.register_next_step_handler(msg, remove_balance_sum)

def remove_balance_sum(m):
    uid = m.text
    msg = bot.send_message(m.chat.id, "Введите сумму:")
    bot.register_next_step_handler(msg, lambda x: change_balance(uid, x, False))

def change_balance(uid, m, add):
    if uid not in users_db["users"]:
        bot.send_message(m.chat.id, "❌ Пользователь не найден")
        return

    if not m.text.isdigit():
        bot.send_message(m.chat.id, "❌ Сумма неверна")
        return

    amount = int(m.text)
    user = users_db["users"][uid]

    user["balance"] += amount if add else -amount
    save_json(USERS_FILE, users_db)

    bot.send_message(m.chat.id, "✅ Баланс обновлён")

# ================= WEBHOOK =================

@app.route(f"/{TOKEN}", methods=["POST"])
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
    bot.set_webhook(url=f"{WEBHOOK_URL}/{TOKEN}")
    app.run(host="0.0.0.0", port=10000)
