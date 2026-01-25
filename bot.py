import telebot
from telebot import types
import json, os
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

def get_user(uid, username):
    uid = str(uid)
    if uid not in users_db["users"]:
        users_db["users"][uid] = {
            "username": username,
            "balance": 0,
            "refs": 0,
            "ref_by": None,
            "verified": False
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
    kb.add("➕ Добавить спонсора", "➖ Удалить спонсора")
    kb.add("📢 Рассылка")
    kb.add("⬅️ Главное меню")
    return kb

# ================= ПРОВЕРКА СПОНСОРОВ =================

def check_subscriptions(user_id):
    for s in sponsors_db["sponsors"]:
        try:
            if s.startswith("@"):
                chat = bot.get_chat_member(s, user_id)
                if chat.status == "left":
                    return False
        except:
            return False
    return True

# ================= START =================

@bot.message_handler(commands=["start"])
def start(m):
    u = get_user(m.from_user.id, m.from_user.username)

    if m.text.split() and len(m.text.split()) > 1:
        ref = m.text.split()[1]
        if ref != str(m.from_user.id):
            u["ref_by"] = ref
            save_json(USERS_FILE, users_db)

    kb = types.InlineKeyboardMarkup()
    for s in sponsors_db["sponsors"]:
        kb.add(types.InlineKeyboardButton("Подписаться", url=s))
    kb.add(types.InlineKeyboardButton("✅ Проверить", callback_data="check"))

    bot.send_message(
        m.chat.id,
        "Привет! Чтобы пользоваться ботом 👇\nПодпишись на всех спонсоров",
        reply_markup=kb
    )

# ================= ПРОВЕРИТЬ =================

@bot.callback_query_handler(func=lambda c: c.data == "check")
def check(c):
    u = get_user(c.from_user.id, c.from_user.username)

    if not check_subscriptions(c.from_user.id):
        bot.answer_callback_query(c.id, "❌ Подпишись на всех спонсоров")
        return

    if not u["verified"]:
        u["verified"] = True

        if u["ref_by"]:
            ref = get_user(u["ref_by"], None)
            ref["balance"] += 1250
            ref["refs"] += 1
            save_json(USERS_FILE, users_db)

            try:
                bot.send_message(int(u["ref_by"]), "У вас новый реферал ☘️")
            except:
                pass

    save_json(USERS_FILE, users_db)
    bot.send_message(c.message.chat.id, "✅ Доступ открыт!", reply_markup=main_menu())

# ================= ПРОФИЛЬ =================

@bot.message_handler(func=lambda m: m.text == "👤 Профиль")
def profile(m):
    u = get_user(m.from_user.id, m.from_user.username)
    bot.send_message(
        m.chat.id,
        f"👤 Профиль\n\n"
        f"ID: {m.from_user.id}\n"
        f"Рефералы: {u['refs']}\n"
        f"Баланс: {u['balance']} Gram"
    )

# ================= ПРИГЛАСИТЬ =================

@bot.message_handler(func=lambda m: m.text == "👥 Пригласить")
def invite(m):
    bot.send_message(
        m.chat.id,
        f"Приглашай друзей и получай 1250 Gram\n\n"
        f"Твоя ссылка:\nhttps://t.me/{bot.get_me().username}?start={m.from_user.id}"
    )

# ================= ВЫВОД =================

@bot.message_handler(func=lambda m: m.text == "💸 Вывод Gram")
def withdraw(m):
    u = get_user(m.from_user.id, m.from_user.username)
    if u["balance"] < 25000:
        bot.send_message(m.chat.id, "Минимальный вывод 25000 Gram")
        return
    msg = bot.send_message(m.chat.id, "Введите сумму для вывода:")
    bot.register_next_step_handler(msg, withdraw_sum)

def withdraw_sum(m):
    u = get_user(m.from_user.id, m.from_user.username)
    try:
        amount = int(m.text)
    except:
        bot.send_message(m.chat.id, "Введите число")
        return

    if amount > u["balance"] or amount < 25000:
        bot.send_message(m.chat.id, "❌ Неверная сумма")
        return

    u["balance"] -= amount
    save_json(USERS_FILE, users_db)

    bot.send_message(
        m.chat.id,
        f"✅ Заявка принята\n\n"
        f"Сумма: {amount} Gram\n"
        f"Напиши администратору для получения"
    )

# ================= АДМИН =================

@bot.message_handler(commands=["admin"])
def admin(m):
    if m.from_user.id in ADMIN_IDS:
        bot.send_message(m.chat.id, "⚙️ Админ панель", reply_markup=admin_menu())

@bot.message_handler(func=lambda m: m.text == "➕ Добавить спонсора" and m.from_user.id in ADMIN_IDS)
def add_sponsor(m):
    msg = bot.send_message(m.chat.id, "Отправь @username или invite-ссылку")
    bot.register_next_step_handler(msg, save_sponsor)

def save_sponsor(m):
    sponsors_db["sponsors"].append(m.text)
    save_json(SPONSORS_FILE, sponsors_db)
    bot.send_message(m.chat.id, "✅ Добавлено")

@bot.message_handler(func=lambda m: m.text == "➖ Удалить спонсора" and m.from_user.id in ADMIN_IDS)
def del_sponsor(m):
    msg = bot.send_message(m.chat.id, "Отправь @username или ссылку")
    bot.register_next_step_handler(msg, remove_sponsor)

def remove_sponsor(m):
    if m.text in sponsors_db["sponsors"]:
        sponsors_db["sponsors"].remove(m.text)
        save_json(SPONSORS_FILE, sponsors_db)
    bot.send_message(m.chat.id, "✅ Удалено")

@bot.message_handler(func=lambda m: m.text == "📢 Рассылка" and m.from_user.id in ADMIN_IDS)
def mailing(m):
    msg = bot.send_message(m.chat.id, "Отправь текст или фото с текстом")
    bot.register_next_step_handler(msg, send_mail)

def send_mail(m):
    for uid in users_db["users"]:
        try:
            if m.content_type == "photo":
                bot.send_photo(uid, m.photo[-1].file_id, caption=m.caption)
            else:
                bot.send_message(uid, m.text)
        except:
            pass
    bot.send_message(m.chat.id, "✅ Рассылка завершена")

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
