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
            "captcha": None,
            "state": None
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
    kb.add("➕ Начислить баланс", "➖ Списать баланс")
    kb.add("📢 Рассылка")
    kb.add("⬅️ Главное меню")
    return kb

# ================= КАПЧА =================

def send_captcha(chat_id, user):
    a, b = random.randint(1, 9), random.randint(1, 9)
    user["captcha"] = a + b
    user["state"] = "captcha"
    save_json(USERS_FILE, users_db)

    bot.send_message(chat_id, f"🔐 Подтвердите, что вы не бот:\n\n{a} + {b} = ?")

# ================= START =================

@bot.message_handler(commands=["start"])
def start(m):
    user = get_user(m.from_user.id, m.from_user.username)

    if user["captcha"] is None:
        send_captcha(m.chat.id, user)
        return

    if len(m.text.split()) > 1:
        ref = m.text.split()[1]
        if ref != str(m.from_user.id):
            user["ref_by"] = ref
            save_json(USERS_FILE, users_db)

    kb = types.InlineKeyboardMarkup()
    for s in sponsors_db["sponsors"]:
        kb.add(types.InlineKeyboardButton("📢 СПОНСОР", url=s))
    kb.add(types.InlineKeyboardButton("✅ Проверить", callback_data="check_subs"))

    bot.send_message(
        m.chat.id,
        "Чтобы пользоваться ботом 👇\nПодпишись на всех спонсоров",
        reply_markup=kb
    )

# ================= ОБРАБОТКА ТЕКСТА =================

@bot.message_handler(content_types=["text", "photo"])
def text_handler(m):
    user = get_user(m.from_user.id, m.from_user.username)

    # КАПЧА
    if user["state"] == "captcha":
        if m.text and m.text.isdigit() and int(m.text) == user["captcha"]:
            user["captcha"] = True
            user["state"] = None
            save_json(USERS_FILE, users_db)
            bot.send_message(m.chat.id, "✅ Капча пройдена\n\nНажми /start")
        else:
            send_captcha(m.chat.id, user)
        return

    # БЛОК ДОСТУПА
    if not user["verified"] and m.text not in ["/start"]:
        bot.send_message(m.chat.id, "❗ Сначала подпишись и нажми «Проверить»")
        return

    # МЕНЮ
    if m.text == "👤 Профиль":
        bot.send_message(
            m.chat.id,
            f"👤 Профиль\n\n"
            f"ID: {m.from_user.id}\n"
            f"Рефералы: {user['refs']}\n"
            f"Баланс: {user['balance']} Gram"
        )

    elif m.text == "👥 Пригласить":
        bot.send_message(
            m.chat.id,
            f"Приглашай друзей и получай 1250 Gram\n\n"
            f"Твоя ссылка:\nhttps://t.me/{bot.get_me().username}?start={m.from_user.id}"
        )

    elif m.text == "💸 Вывод Gram":
        if user["balance"] < 25000:
            bot.send_message(m.chat.id, "❌ Минимальный вывод 25000 Gram")
            return
        user["state"] = "withdraw"
        save_json(USERS_FILE, users_db)
        bot.send_message(m.chat.id, "Введите сумму для вывода:")

    elif user["state"] == "withdraw":
        if not m.text.isdigit():
            bot.send_message(m.chat.id, "Введите число")
            return
        amount = int(m.text)
        if amount < 25000 or amount > user["balance"]:
            bot.send_message(m.chat.id, "❌ Неверная сумма")
            return

        user["balance"] -= amount
        user["state"] = None
        save_json(USERS_FILE, users_db)

        bot.send_message(
            m.chat.id,
            f"✅ Заявка на вывод принята\n\n"
            f"💰 Сумма: {amount} Gram\n\n"
            f"📌 Для получения:\n"
            f"1️⃣ Перейди в группу\n"
            f"https://t.me/+5yNBdXSxMoMzMzVi\n\n"
            f"2️⃣ Напиши администратору\n"
            f"3️⃣ Ожидай выплату до 24 часов"
        )

    # АДМИНКА
    if m.from_user.id in ADMIN_IDS:
        if m.text == "/admin":
            bot.send_message(m.chat.id, "⚙️ Админ панель", reply_markup=admin_menu())

        elif m.text == "⬅️ Главное меню":
            bot.send_message(m.chat.id, "Главное меню", reply_markup=main_menu())

        elif m.text == "➕ Добавить спонсора":
            user["state"] = "add_sponsor"
            save_json(USERS_FILE, users_db)
            bot.send_message(m.chat.id, "Отправь @username или invite-ссылку")

        elif user["state"] == "add_sponsor":
            sponsors_db["sponsors"].append(m.text)
            user["state"] = None
            save_json(SPONSORS_FILE, sponsors_db)
            save_json(USERS_FILE, users_db)
            bot.send_message(m.chat.id, "✅ Спонсор добавлен")

        elif m.text == "➖ Удалить спонсора":
            user["state"] = "del_sponsor"
            save_json(USERS_FILE, users_db)
            bot.send_message(m.chat.id, "Отправь @username или ссылку")

        elif user["state"] == "del_sponsor":
            if m.text in sponsors_db["sponsors"]:
                sponsors_db["sponsors"].remove(m.text)
                save_json(SPONSORS_FILE, sponsors_db)
            user["state"] = None
            save_json(USERS_FILE, users_db)
            bot.send_message(m.chat.id, "✅ Спонсор удалён")

        elif m.text == "📢 Рассылка":
            user["state"] = "mailing"
            save_json(USERS_FILE, users_db)
            bot.send_message(m.chat.id, "Отправь текст или фото")

        elif user["state"] == "mailing":
            for uid in users_db["users"]:
                try:
                    if m.content_type == "photo":
                        bot.send_photo(uid, m.photo[-1].file_id, caption=m.caption)
                    else:
                        bot.send_message(uid, m.text)
                except:
                    pass
            user["state"] = None
            save_json(USERS_FILE, users_db)
            bot.send_message(m.chat.id, "✅ Рассылка завершена")

# ================= ПРОВЕРКА СПОНСОРОВ =================

@bot.callback_query_handler(func=lambda c: c.data == "check_subs")
def check_subs(c):
    user = get_user(c.from_user.id, c.from_user.username)

    for s in sponsors_db["sponsors"]:
        if s.startswith("@"):
            try:
                member = bot.get_chat_member(s, c.from_user.id)
                if member.status == "left":
                    bot.answer_callback_query(c.id, "❌ Подпишись на всех")
                    return
            except:
                bot.answer_callback_query(c.id, "❌ Ошибка проверки")
                return

    if not user["verified"]:
        user["verified"] = True
        if user["ref_by"]:
            ref = get_user(user["ref_by"])
            ref["balance"] += 1250
            ref["refs"] += 1
            try:
                bot.send_message(int(user["ref_by"]), "☘️ У вас новый реферал")
            except:
                pass

    save_json(USERS_FILE, users_db)
    bot.send_message(c.message.chat.id, "✅ Доступ открыт", reply_markup=main_menu())

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
