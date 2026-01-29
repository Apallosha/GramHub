import telebot
from telebot import types
from flask import Flask, request
import os, json, random

# ================= НАСТРОЙКИ =================

TOKEN = "8275742360:AAFDN-FBvQtgdTNeCOd9nlWXJFXQS_4LbaU"
ADMIN_IDS = [5333130126]  # <-- ТВОЙ TELEGRAM ID
NEWS_CHANNEL = "@GramHubNews"  # новостник (публичный)

WEBHOOK_URL = "https://gramhub-2qn6.onrender.com"

USERS_FILE = "users.json"
SPONSORS_FILE = "sponsors.json"

MIN_WITHDRAW = 25000
REF_BONUS = 1250

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# ================= УТИЛИТЫ =================

def load_json(path, default):
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(default, f)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def get_user(uid, username=""):
    users = load_json(USERS_FILE, {})
    if str(uid) not in users:
        users[str(uid)] = {
            "balance": 0,
            "refs": 0,
            "invited_by": None,
            "captcha": None,
            "sub_ok": False
        }
        save_json(USERS_FILE, users)
    return users[str(uid)]

def update_user(uid, data):
    users = load_json(USERS_FILE, {})
    users[str(uid)] = data
    save_json(USERS_FILE, users)

def is_admin(uid):
    return uid in ADMIN_IDS

# ================= КЛАВИАТУРЫ =================

def main_menu(uid):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("👤 Профиль", "👥 Пригласить")
    kb.add("💸 Вывод Gram")
    if is_admin(uid):
        kb.add("⚙ Админка")
    return kb

def sponsors_kb():
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("📰 Новостник", url=f"https://t.me/{NEWS_CHANNEL.replace('@','')}"))
    sponsors = load_json(SPONSORS_FILE, [])
    for s in sponsors:
        kb.add(types.InlineKeyboardButton("💎 СПОНСОР", url=s))
    kb.add(types.InlineKeyboardButton("✅ Проверить", callback_data="check_subs"))
    return kb

# ================= /START + КАПЧА =================

@bot.message_handler(commands=["start"])
def start(m):
    uid = m.from_user.id
    username = m.from_user.username or ""
    user = get_user(uid, username)

    if len(m.text.split()) > 1:
        ref = m.text.split()[1]
        if user["invited_by"] is None and ref != str(uid):
            user["invited_by"] = ref
            update_user(uid, user)

    a, b = random.randint(1, 9), random.randint(1, 9)
    user["captcha"] = a + b
    update_user(uid, user)

    bot.send_message(
        uid,
        f"🤖 Реши капчу:\n\n{a} + {b} = ?"
    )

@bot.message_handler(func=lambda m: m.text.isdigit())
def captcha_check(m):
    uid = m.from_user.id
    user = get_user(uid)

    if user["captcha"] is None:
        return

    if int(m.text) == user["captcha"]:
        user["captcha"] = None
        update_user(uid, user)
        bot.send_message(
            uid,
            "Привет подпишись на всех спонсоров что бы пользоваться ботом!",
            reply_markup=sponsors_kb()
        )
    else:
        bot.send_message(uid, "❌ Неверно, попробуй ещё раз")

# ================= ПРОВЕРКА ПОДПИСКИ =================

@bot.callback_query_handler(func=lambda c: c.data == "check_subs")
def check_subs(c):
    uid = c.from_user.id
    sponsors = load_json(SPONSORS_FILE, [])
    channels = [NEWS_CHANNEL] + sponsors

    for ch in channels:
        try:
            status = bot.get_chat_member(ch, uid).status
            if status not in ["member", "administrator", "creator"]:
                bot.answer_callback_query(c.id, "❌ Ты не подписан на всех", show_alert=True)
                return
        except:
            bot.answer_callback_query(c.id, "❌ Ошибка проверки подписки", show_alert=True)
            return

    user = get_user(uid)
    if not user["sub_ok"]:
        user["sub_ok"] = True

        if user["invited_by"]:
            inviter = get_user(user["invited_by"])
            inviter["balance"] += REF_BONUS
            inviter["refs"] += 1
            update_user(user["invited_by"], inviter)

    update_user(uid, user)

    bot.send_message(
        uid,
        "Привет! Этот бот создан для заработка Gram!\n"
        "Приглашай друзей - зарабатывай - выводи! Все просто ☘️",
        reply_markup=main_menu(uid)
    )

# ================= ПРОФИЛЬ =================

@bot.message_handler(func=lambda m: m.text == "👤 Профиль")
def profile(m):
    u = get_user(m.from_user.id)
    bot.send_message(
        m.chat.id,
        f"Привет {m.from_user.username}!\n\n"
        f"ID: {m.from_user.id}\n"
        f"Баланс: {u['balance']} Gram\n"
        f"Рефералов: {u['refs']}\n\n"
        f"Приглашай друзей и получай по 1.250GRAM!\n"
        f"Твоя ссылка:\n"
        f"https://t.me/{bot.get_me().username}?start={m.from_user.id}"
    )

# ================= ПРИГЛАСИТЬ =================

@bot.message_handler(func=lambda m: m.text == "👥 Пригласить")
def invite(m):
    bot.send_message(
        m.chat.id,
        f"Привет {m.from_user.username}!\n"
        f"Приглашай друзей и получай 1.250GRAM!\n\n"
        f"> P.s реферал засчитывается после подписки на всех спонсоров!\n\n"
        f"Твоя ссылка:\n"
        f"https://t.me/{bot.get_me().username}?start={m.from_user.id}"
    )

# ================= ВЫВОД =================

withdraw_wait = {}

@bot.message_handler(func=lambda m: m.text == "💸 Вывод Gram")
def withdraw(m):
    u = get_user(m.from_user.id)
    if u["balance"] < MIN_WITHDRAW:
        bot.send_message(
            m.chat.id,
            "❌ Не достаточно Gram для вывода.\nМинимальный вывод 25k Gram!"
        )
        return

    withdraw_wait[m.from_user.id] = True
    bot.send_message(m.chat.id, "Введи сумму для вывода (не меньше 25k):")

@bot.message_handler(func=lambda m: m.from_user.id in withdraw_wait)
def withdraw_amount(m):
    uid = m.from_user.id
    if not m.text.isdigit():
        return

    amount = int(m.text)
    u = get_user(uid)

    if amount < MIN_WITHDRAW or u["balance"] < amount:
        bot.send_message(uid, "❌ Не достаточно Gram для вывода.")
        withdraw_wait.pop(uid)
        return

    u["balance"] -= amount
    update_user(uid, u)
    withdraw_wait.pop(uid)

    bot.send_message(
        uid,
        "Для вывода Gram осталось не много!\n\n"
        "1. Сделай скриншот суммы вывода в боте\n"
        "2. Зайди в https://t.me/+5yNBdXSxMoMzMzVi\n"
        "3. Скинь скриншот и ожидай вывод 2-3 дня\n\n"
        "Удачи ☘️"
    )

# ================= АДМИНКА =================

admin_state = {}

@bot.message_handler(func=lambda m: m.text == "⚙ Админка" and is_admin(m.from_user.id))
def admin(m):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("➕➖ Спонсор", "💰 Баланс")
    kb.add("📢 Рассылка", "⬅ Назад")
    bot.send_message(m.chat.id, "⚙ Админка", reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == "➕➖ Спонсор" and is_admin(m.from_user.id))
def sponsor_edit(m):
    admin_state[m.from_user.id] = "sponsor"
    bot.send_message(m.chat.id, "Отправь @юзернейм или ссылку канала")

@bot.message_handler(func=lambda m: admin_state.get(m.from_user.id) == "sponsor")
def sponsor_save(m):
    sponsors = load_json(SPONSORS_FILE, [])
    if m.text in sponsors:
        sponsors.remove(m.text)
        bot.send_message(m.chat.id, "❌ Спонсор удалён")
    else:
        sponsors.append(m.text)
        bot.send_message(m.chat.id, "✅ Спонсор добавлен")
    save_json(SPONSORS_FILE, sponsors)
    admin_state.pop(m.from_user.id)

@bot.message_handler(func=lambda m: m.text == "💰 Баланс" and is_admin(m.from_user.id))
def balance_admin(m):
    admin_state[m.from_user.id] = "balance"
    bot.send_message(m.chat.id, "Отправь: ID СУММА (минус для списания)")

@bot.message_handler(func=lambda m: admin_state.get(m.from_user.id) == "balance")
def balance_edit(m):
    uid, amount = m.text.split()
    u = get_user(uid)
    u["balance"] += int(amount)
    update_user(uid, u)
    bot.send_message(m.chat.id, "✅ Баланс обновлён")
    admin_state.pop(m.from_user.id)

@bot.message_handler(func=lambda m: m.text == "📢 Рассылка" and is_admin(m.from_user.id))
def broadcast(m):
    admin_state[m.from_user.id] = "broadcast"
    bot.send_message(m.chat.id, "Отправь текст / фото / текст+фото")

@bot.message_handler(func=lambda m: admin_state.get(m.from_user.id) == "broadcast", content_types=["text", "photo"])
def send_all(m):
    users = load_json(USERS_FILE, {})
    for uid in users:
        try:
            if m.content_type == "text":
                bot.send_message(uid, m.text)
            else:
                bot.send_photo(uid, m.photo[-1].file_id, caption=m.caption)
        except:
            pass
    bot.send_message(m.chat.id, "✅ Рассылка завершена")
    admin_state.pop(m.from_user.id)

# ================= WEBHOOK =================

@app.route("/webhook", methods=["POST"])
def webhook():
    bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
    return "OK", 200

if __name__ == "__main__":
    bot.remove_webhook()
    bot.set_webhook(WEBHOOK_URL)
    app.run(host="0.0.0.0", port=10000)
