import telebot
from telebot import types
import json, os, random
from flask import Flask, request

# ================= НАСТРОЙКИ =================
TOKEN = "8275742360:AAFDN-FBvQtgdTNeCOd9nlWXJFXQS_4LbaU"
ADMIN_IDS = [5333130126]
NEWS_CHANNEL = "@GramHubNews"

WEBHOOK_PATH = f"/webhook/{TOKEN}"
WEBHOOK_URL = f"https://gramhub-2qn6.onrender.com{WEBHOOK_PATH}"

USERS_FILE = "users.json"
SPONSORS_FILE = "sponsors.json"

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# ================= ХРАНЕНИЕ =================
def load_json(path, default):
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(default, f, ensure_ascii=False, indent=2)
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_user(uid, username):
    db = load_json(USERS_FILE, {"users": {}})
    users = db["users"]
    uid = str(uid)

    if uid not in users:
        users[uid] = {
            "id": int(uid),
            "username": username or "",
            "balance": 0,
            "refs": 0
        }
        save_json(USERS_FILE, db)

    return users[uid]

# ================= ПРОВЕРКИ =================
def is_admin(uid):
    return uid in ADMIN_IDS

def get_chat_id_from_invite(link):
    try:
        chat = bot.get_chat(link)
        return chat.id
    except:
        return None

def check_subscription(user_id):
    data = load_json(SPONSORS_FILE, {"sponsors": []})

    for sponsor in data["sponsors"]:
        try:
            if sponsor.startswith("@"):
                chat_id = sponsor
            elif sponsor.startswith("https://t.me/"):
                chat_id = get_chat_id_from_invite(sponsor)
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
    kb.add("👤 Профиль", "👥 Пригласить")
    kb.add("💸 Вывод Gram")
    return kb

def admin_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("➕ Добавить спонсора", "➖ Удалить спонсора")
    kb.add("📢 Рассылка")
    kb.add("🏠 Главное меню")
    return kb

# ================= /start =================
@bot.message_handler(commands=["start"])
def start(m):
    uid = m.from_user.id
    user = get_user(uid, m.from_user.username)

    if not check_subscription(uid):
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("📢 Новостник GramHub", url=f"https://t.me/{NEWS_CHANNEL.lstrip('@')}"))

        sponsors = load_json(SPONSORS_FILE, {"sponsors": []})["sponsors"]
        for s in sponsors:
            kb.add(types.InlineKeyboardButton("СПОНСОР", url=s))

        kb.add(types.InlineKeyboardButton("✅ Проверить", callback_data="check_sub"))

        bot.send_message(
            m.chat.id,
            f"Привет, {m.from_user.first_name}!\n\n"
            "Для начала подпишись на все каналы ниже 👇",
            reply_markup=kb
        )
        return

    text = (
        f"Привет {m.from_user.first_name}! Ты попал в лучшего бота по заработку Gram, "
        "приглашай друзей по реферальной ссылке и зарабатывай Gram!"
    )

    if is_admin(uid):
        bot.send_message(m.chat.id, text, reply_markup=admin_menu())
    else:
        bot.send_message(m.chat.id, text, reply_markup=main_menu())

# ================= CALLBACK =================
@bot.callback_query_handler(func=lambda c: c.data == "check_sub")
def cb_check(c):
    if check_subscription(c.from_user.id):
        bot.answer_callback_query(c.id, "✅ Подписка подтверждена")
        start(c.message)
    else:
        bot.answer_callback_query(c.id, "❌ Подпишись на все каналы")

# ================= ПРОФИЛЬ =================
@bot.message_handler(func=lambda m: m.text == "👤 Профиль")
def profile(m):
    u = get_user(m.from_user.id, m.from_user.username)
    bot.send_message(
        m.chat.id,
        f"Профиль {m.from_user.first_name}\n\n"
        f"ID: {u['id']}\n"
        f"Рефералы: {u['refs']}\n"
        f"Баланс Gram: {u['balance']}"
    )

# ================= ПРИГЛАСИТЬ =================
@bot.message_handler(func=lambda m: m.text == "👥 Пригласить")
def invite(m):
    bot.send_message(
        m.chat.id,
        f"Привет {m.from_user.first_name}! Приглашай друзей и зарабатывай Gram!\n\n"
        "Реферал считается после подписки на всех спонсоров!\n\n"
        f"Твоя ссылка:\nhttps://t.me/{bot.get_me().username}?start={m.from_user.id}"
    )

# ================= ВЫВОД =================
@bot.message_handler(func=lambda m: m.text == "💸 Вывод Gram")
def withdraw(m):
    u = get_user(m.from_user.id, m.from_user.username)
    if u["balance"] < 20000:
        bot.send_message(m.chat.id, "Минимальный вывод 20000 Gram")
        return

    bot.send_message(
        m.chat.id,
        "Для вывода Gram зайди в группу:\n"
        "https://t.me/+5yNBdXSxMoMzMzVi\n\n"
        "Ожидай вывод в течение 24 часов!"
    )

# ================= АДМИНКА =================
@bot.message_handler(func=lambda m: is_admin(m.from_user.id) and m.text == "➕ Добавить спонсора")
def add_sponsor(m):
    bot.send_message(m.chat.id, "Отправь @канал или invite-link")
    bot.register_next_step_handler(m, save_sponsor)

def save_sponsor(m):
    data = load_json(SPONSORS_FILE, {"sponsors": []})
    data["sponsors"].append(m.text.strip())
    save_json(SPONSORS_FILE, data)
    bot.send_message(m.chat.id, "✅ Спонсор добавлен", reply_markup=admin_menu())

@bot.message_handler(func=lambda m: is_admin(m.from_user.id) and m.text == "➖ Удалить спонсора")
def del_sponsor(m):
    bot.send_message(m.chat.id, "Отправь ссылку или @ для удаления")
    bot.register_next_step_handler(m, remove_sponsor)

def remove_sponsor(m):
    data = load_json(SPONSORS_FILE, {"sponsors": []})
    if m.text in data["sponsors"]:
        data["sponsors"].remove(m.text)
        save_json(SPONSORS_FILE, data)
        bot.send_message(m.chat.id, "✅ Удалено", reply_markup=admin_menu())
    else:
        bot.send_message(m.chat.id, "❌ Не найдено")

@bot.message_handler(func=lambda m: is_admin(m.from_user.id) and m.text == "📢 Рассылка")
def mailing(m):
    bot.send_message(m.chat.id, "Отправь сообщение для рассылки")
    bot.register_next_step_handler(m, send_mail)

def send_mail(m):
    db = load_json(USERS_FILE, {"users": {}})
    sent = 0
    for uid in db["users"]:
        try:
            bot.send_message(int(uid), m.text)
            sent += 1
        except:
            pass
    bot.send_message(m.chat.id, f"📢 Отправлено: {sent}", reply_markup=admin_menu())

@bot.message_handler(func=lambda m: is_admin(m.from_user.id) and m.text == "🏠 Главное меню")
def admin_home(m):
    bot.send_message(m.chat.id, "Главное меню", reply_markup=admin_menu())

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
