import telebot
from telebot import types
import json, os, random
from flask import Flask, request

# ================= НАСТРОЙКИ =================
TOKEN = "8275742360:AAFDN-FBvQtgdTNeCOd9nlWXJFXQS_4LbaU"
ADMIN_IDS = [5333130126]
NEWS_CHANNEL = "@GramHubNews"

WEBHOOK_PATH = f"/webhook/{TOKEN}"
WEBHOOK_URL = f"https://gramhub-2qn6.onrender.com{WEBHOOK_PATH}"  # Замените на свой URL

USERS_FILE = "users.json"
SPONSORS_FILE = "sponsors.json"

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# ================= JSON =================
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
            "captcha": False,
            "subscribed": False,
            "ref_added": False,
            "last_checked_sponsors": []
        }
        save_json(USERS_FILE, users_db)
    return users_db["users"][uid]

captcha_answers = {}

# ================= КАПЧА =================
def send_captcha(m):
    a, b = random.randint(1,5), random.randint(1,5)
    captcha_answers[m.from_user.id] = a + b
    bot.send_message(m.chat.id, f"🤖 Докажи, что ты не бот!\n\nСколько будет {a} + {b}?")

@bot.message_handler(func=lambda m: m.from_user.id in captcha_answers)
def check_captcha(m):
    if not m.text.isdigit(): return
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
    try:
        member = bot.get_chat_member(NEWS_CHANNEL, uid)
        if member.status not in ["member", "administrator", "creator"]:
            return False
    except:
        return False
    for s in sponsors_db["sponsors"]:
        try:
            member = bot.get_chat_member(s, uid)
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
    kb.add("⬅️ Назад в меню")
    return kb

def sponsors_kb():
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("📰 Новостник GramHub", url=f"https://t.me/{NEWS_CHANNEL[1:]}"))
    for s in sponsors_db["sponsors"]:
        kb.add(types.InlineKeyboardButton("💎 СПОНСОР", url=s))
    kb.add(types.InlineKeyboardButton("✅ Проверить", callback_data="check_subs"))
    return kb

# ================= START =================
@bot.message_handler(commands=["start"])
def start(m):
    args = m.text.split()
    u = get_user(m.from_user.id, m.from_user.username)

    # Сохраняем inviter_id
    if len(args) > 1 and u["inviter"] is None:
        inviter_id = args[1]
        if inviter_id != str(m.from_user.id) and inviter_id in users_db["users"]:
            u["inviter"] = inviter_id
            save_json(USERS_FILE, users_db)

    if not u["captcha"]:
        send_captcha(m)
        return

    send_welcome(m)

def send_welcome(m):
    text = f"Привет {m.from_user.username or m.from_user.first_name}!\n\n" \
           "Ты попал в лучшего бота по заработку Gram, приглашай друзей и зарабатывай Gram!\n\n" \
           "❝ Для начала подпишись на все каналы ниже 👇 ❞"
    bot.send_message(m.chat.id, text, reply_markup=sponsors_kb())

# ================= НОВЫЕ СПОНСОРЫ =================
def check_new_sponsors(uid, chat_id):
    u = get_user(uid, "")
    new_spons = [s for s in sponsors_db["sponsors"] if s not in u["last_checked_sponsors"]]
    if new_spons:
        u["last_checked_sponsors"] = sponsors_db["sponsors"].copy()
        save_json(USERS_FILE, users_db)
        bot.send_message(chat_id, "❗ Появились новые каналы, подпишись на них и нажми Проверить снова.", reply_markup=sponsors_kb())
        return True
    return False

# ================= CALLBACK =================
@bot.callback_query_handler(func=lambda c: c.data == "check_subs")
def check_subs(c):
    if check_new_sponsors(c.from_user.id, c.message.chat.id):
        return

    if not is_subscribed(c.from_user.id):
        bot.answer_callback_query(c.id, "❌ Ты не подписан на все обязательные каналы!", show_alert=True)
        return

    u = get_user(c.from_user.id, c.from_user.username)
    # Засчитываем реферал
    if u["inviter"] and not u.get("ref_added", False):
        inviter_id = u["inviter"]
        users_db["users"][inviter_id]["refs"] += 1
        users_db["users"][inviter_id]["balance"] += 1250
        u["ref_added"] = True
        save_json(USERS_FILE, users_db)
        try:
            bot.send_message(inviter_id, "У вас новый реферал ☘️")
        except: pass

    u["subscribed"] = True
    save_json(USERS_FILE, users_db)
    bot.send_message(c.message.chat.id, "✅ Подписка подтверждена!", reply_markup=main_menu())

# ================= МЕНЮ =================
def button_check_subscription(func):
    def wrapper(m):
        if check_new_sponsors(m.from_user.id, m.chat.id):
            return
        return func(m)
    return wrapper

@bot.message_handler(func=lambda m: m.text == "👤 Профиль")
@button_check_subscription
def profile(m):
    u = get_user(m.from_user.id, m.from_user.username)
    bot.send_message(m.chat.id,
                     f"Профиль {m.from_user.username}\n\n"
                     f"ID: {m.from_user.id}\n"
                     f"Рефералы: {u['refs']}\n"
                     f"Баланс Gram: {u['balance']}")

@bot.message_handler(func=lambda m: m.text == "👥 Пригласить")
@button_check_subscription
def invite(m):
    bot.send_message(m.chat.id,
                     f"Привет {m.from_user.username}!\n\n"
                     "Приглашай друзей и зарабатывай Gram, "
                     "за одного реферала ты получишь 1250 Gram!\n\n"
                     "❝ Реферал засчитывается после подписки на все обязательные каналы! ❞\n\n"
                     f"Твоя ссылка:\nhttps://t.me/{bot.get_me().username}?start={m.from_user.id}")

@bot.message_handler(func=lambda m: m.text == "💸 Вывод Gram")
@button_check_subscription
def withdraw(m):
    u = get_user(m.from_user.id, m.from_user.username)
    if u["balance"] < 25000:
        bot.send_message(m.chat.id, "Минимальный вывод 25000 Gram")
        return
    msg = bot.send_message(m.chat.id,
                     f"💸 Введите сумму для вывода\nМинимум: 25000 Gram\nВаш баланс: {u['balance']} Gram")
    bot.register_next_step_handler(msg, process_withdraw)

def process_withdraw(m):
    if not m.text.isdigit(): return
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
    bot.send_message(m.chat.id,
                     "✅ Gram успешно списаны!\n\n"
                     "Для получения Gram зайди в группу:\n"
                     "https://t.me/+5yNBdXSxMoMzMzVi\n\n"
                     "⏳ Ожидай вывод в течение 24 часов!")

# ================= АДМИН =================
@bot.message_handler(commands=["admin"])
def admin_cmd(m):
    if m.from_user.id not in ADMIN_IDS: return
    bot.send_message(m.chat.id, "⚙️ Админ панель", reply_markup=admin_menu())

@bot.message_handler(func=lambda m: m.text == "⬅️ Назад в меню" and m.from_user.id in ADMIN_IDS)
def admin_back(m):
    bot.send_message(m.chat.id, "Главное меню", reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text == "➕ Добавить спонсора" and m.from_user.id in ADMIN_IDS)
def add_sponsor(m):
    msg = bot.send_message(m.chat.id, "Отправь @юзер канала или invite-ссылку приватного канала")
    bot.register_next_step_handler(msg, save_sponsor)

def save_sponsor(m):
    text = m.text.strip()
    if text.startswith("@") or text.startswith("https://t.me/+"):
        sponsors_db["sponsors"].append(text)
        save_json(SPONSORS_FILE, sponsors_db)
        bot.send_message(m.chat.id, "✅ Спонсор добавлен")
    else:
        bot.send_message(m.chat.id, "❌ Неверный формат")

@bot.message_handler(func=lambda m: m.text == "➖ Удалить спонсора" and m.from_user.id in ADMIN_IDS)
def del_sponsor(m):
    msg = bot.send_message(m.chat.id, "Отправь @юзер или invite-ссылку")
    bot.register_next_step_handler(msg, remove_sponsor)

def remove_sponsor(m):
    text = m.text.strip()
    if text in sponsors_db["sponsors"]:
        sponsors_db["sponsors"].remove(text)
        save_json(SPONSORS_FILE, sponsors_db)
        bot.send_message(m.chat.id, "✅ Спонсор удалён")
    else:
        bot.send_message(m.chat.id, "❌ Спонсор не найден")

@bot.message_handler(func=lambda m: m.text == "📢 Рассылка" and m.from_user.id in ADMIN_IDS)
def mailing(m):
    msg = bot.send_message(m.chat.id, "Отправь текст для рассылки")
    bot.register_next_step_handler(msg, send_mail)

def send_mail(m):
    text = m.text
    success = 0
    fail = 0
    for uid_str in users_db["users"]:
        try:
            uid = int(uid_str)
            bot.send_message(uid, text)
            success += 1
        except:
            fail += 1
    bot.send_message(m.chat.id, f"✅ Рассылка завершена!\nДоставлено: {success}\nНе доставлено: {fail}")

# ================= WEBHOOK =================
@app.route(WEBHOOK_PATH, methods=["POST"])
def webhook():
    update = telebot.types.Update.de_json(request.stream.read().decode("utf-8"))
    bot.process_new_updates([update])
    return "OK", 200

@app.route("/")
def index():
    return "Bot is alive", 200

if __name__ == "__main__":
    try:
        bot.remove_webhook()
        bot.set_webhook(url=WEBHOOK_URL)
        print("Webhook установлен")
    except:
        print("Webhook не установлен, запускаем polling")
        bot.infinity_polling()
    app.run(host="0.0.0.0", port=10000)
