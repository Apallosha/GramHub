import telebot
from telebot import types
import os
import threading
from flask import Flask
import storage

# ========= НАСТРОЙКИ =========
TOKEN = os.getenv("TOKEN") or "8275742360:AAFDN-FBvQtgdTNeCOd9nlWXJFXQS_4LbaU"
ADMIN_IDS = [5333130126]
NEWS_CHANNEL = "@GramHubNews"
REF_REWARD = 1250
MIN_WITHDRAW = 20000

# ========= FLASK =========
app = Flask(__name__)

@app.route("/")
def home():
    return "OK"

def run_flask():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

threading.Thread(target=run_flask).start()

# ========= BOT =========
bot = telebot.TeleBot(TOKEN)
db = storage.load()

# ========= KEYBOARDS =========
def main_menu(is_admin=False):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("👤 Профиль", "🤝 Пригласить")
    kb.add("💸 Вывод Gram")
    if is_admin:
        kb.add("🛠 Админка")
    return kb

def admin_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("➕ Добавить спонсора", "➖ Удалить спонсора")
    kb.add("📢 Рассылка")
    kb.add("🏠 Главное меню")
    return kb

# ========= START + CAPTCHA =========
@bot.message_handler(commands=["start"])
def start(m):
    user = storage.get_user(db, m.from_user.id, m.from_user.username)
    user["state"] = "captcha"
    storage.save(db)

    bot.send_message(
        m.chat.id,
        "Подтверди что ты не бот 🤖\n\nСколько будет 2 + 1 ?"
    )

# ========= CAPTCHA =========
@bot.message_handler(func=lambda m: True)
def all_messages(m):
    uid = str(m.from_user.id)
    if uid not in db["users"]:
        return

    user = db["users"][uid]

    # КАПЧА
    if user["state"] == "captcha":
        if m.text.strip() == "3":
            user["state"] = None
            storage.save(db)
            send_welcome(m)
        else:
            bot.send_message(m.chat.id, "❌ Неверно, попробуй ещё раз")
        return

    # ВВОД СУММЫ ВЫВОДА
    if user["state"] == "withdraw":
        if not m.text.isdigit():
            bot.send_message(m.chat.id, "Введи число")
            return

        amount = int(m.text)
        if amount < MIN_WITHDRAW:
            bot.send_message(m.chat.id, f"Минимальный вывод {MIN_WITHDRAW} Gram")
            return

        if user["balance"] < amount:
            bot.send_message(m.chat.id, "Недостаточно Gram для вывода!")
            return

        user["balance"] -= amount
        user["state"] = None
        storage.save(db)

        bot.send_message(
            m.chat.id,
            "Дальше для вывода Gram зайди в группу:\n"
            "https://t.me/+5yNBdXSxMoMzMzVi\n\n"
            "и ожидай вывода в течении 24 часов!"
        )
        return

    # ===== КНОПКИ =====
    if m.text == "👤 Профиль":
        profile(m)
    elif m.text == "🤝 Пригласить":
        invite(m)
    elif m.text == "💸 Вывод Gram":
        withdraw(m)
    elif m.text == "🛠 Админка" and m.from_user.id in ADMIN_IDS:
        bot.send_message(m.chat.id, "Админка", reply_markup=admin_menu())
    elif m.text == "🏠 Главное меню":
        bot.send_message(m.chat.id, "Главное меню", reply_markup=main_menu(m.from_user.id in ADMIN_IDS))

# ========= WELCOME =========
def send_welcome(m):
    text = (
        f"Привет {m.from_user.first_name}! Ты попал в лучшего бота по заработку Gram,\n"
        "приглашай друзей по реферальной ссылке и зарабатывай Gram!\n\n"
        "Для начала подпишись на все каналы ниже 👇"
    )

    ikb = types.InlineKeyboardMarkup()
    ikb.add(types.InlineKeyboardButton(
        "📢 Новостник GramHub",
        url=f"https://t.me/{NEWS_CHANNEL.replace('@','')}"
    ))

    for s in db["sponsors"]:
        ikb.add(types.InlineKeyboardButton("🔔 СПОНСОР", url=f"https://t.me/{s.replace('@','')}"))

    ikb.add(types.InlineKeyboardButton("✅ Проверить", callback_data="check"))

    bot.send_message(m.chat.id, text, reply_markup=ikb)

# ========= CHECK =========
@bot.callback_query_handler(func=lambda c: c.data == "check")
def check(c):
    uid = c.from_user.id
    for s in db["sponsors"]:
        try:
            member = bot.get_chat_member(s, uid)
            if member.status not in ["member", "administrator", "creator"]:
                raise Exception
        except:
            bot.answer_callback_query(c.id, "Подпишись на все каналы!", show_alert=True)
            return

    bot.send_message(uid, "Подписка подтверждена ✅", reply_markup=main_menu(uid in ADMIN_IDS))

# ========= USER =========
def profile(m):
    u = db["users"][str(m.from_user.id)]
    bot.send_message(
        m.chat.id,
        f"Профиль {m.from_user.first_name}\n\n"
        f"ID: {u['id']}\n"
        f"Рефералы: {u['refs']}\n"
        f"Баланс Gram: {u['balance']}",
        reply_markup=main_menu(m.from_user.id in ADMIN_IDS)
    )

def invite(m):
    link = f"https://t.me/{bot.get_me().username}?start={m.from_user.id}"
    bot.send_message(
        m.chat.id,
        f"Привет {m.from_user.first_name}!\n"
        "Приглашай друзей и зарабатывай Gram, за одного реферала ты получишь 1250 Gram!\n\n"
        "Реферал считается после подписки на всех спонсоров!\n\n"
        f"Твоя ссылка:\n{link}",
        reply_markup=main_menu(m.from_user.id in ADMIN_IDS)
    )

def withdraw(m):
    user = db["users"][str(m.from_user.id)]
    if user["balance"] < MIN_WITHDRAW:
        bot.send_message(m.chat.id, f"Минимальный вывод {MIN_WITHDRAW} Gram")
    else:
        user["state"] = "withdraw"
        storage.save(db)
        bot.send_message(m.chat.id, "Введи сумму для вывода")

# ========= ADMIN =========
@bot.message_handler(func=lambda m: m.text == "➕ Добавить спонсора" and m.from_user.id in ADMIN_IDS)
def add_s(m):
    bot.send_message(m.chat.id, "Отправь @username канала")
    bot.register_next_step_handler(m, save_s)

def save_s(m):
    if m.text.startswith("@"):
        db["sponsors"].append(m.text)
        storage.save(db)
        bot.send_message(m.chat.id, "Спонсор добавлен", reply_markup=admin_menu())

@bot.message_handler(func=lambda m: m.text == "➖ Удалить спонсора" and m.from_user.id in ADMIN_IDS)
def del_s(m):
    bot.send_message(m.chat.id, "Отправь @username для удаления")
    bot.register_next_step_handler(m, del_s2)

def del_s2(m):
    if m.text in db["sponsors"]:
        db["sponsors"].remove(m.text)
        storage.save(db)
        bot.send_message(m.chat.id, "Удалено", reply_markup=admin_menu())

@bot.message_handler(func=lambda m: m.text == "📢 Рассылка" and m.from_user.id in ADMIN_IDS)
def bc(m):
    bot.send_message(m.chat.id, "Отправь текст рассылки")
    bot.register_next_step_handler(m, do_bc)

def do_bc(m):
    sent = 0
    for uid in db["users"]:
        try:
            bot.send_message(uid, m.text)
            sent += 1
        except:
            pass
    bot.send_message(m.chat.id, f"Рассылка отправлена ({sent})", reply_markup=admin_menu())

# ========= RUN =========
print("Bot started")
bot.infinity_polling()
