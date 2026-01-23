import telebot
from telebot import types
import json
import os
import threading
from flask import Flask

# ================= НАСТРОЙКИ =================
TOKEN = os.getenv("TOKEN") or "8275742360:AAFDN-FBvQtgdTNeCOd9nlWXJFXQS_4LbaU"
ADMIN_IDS = [5333130126]  # ← ТВОЙ ID
NEWS_CHANNEL = "@GramHubNews"  # Новостник
REF_REWARD = 1250
MIN_WITHDRAW = 20000
DB_FILE = "db.json"

# ================= FLASK (UPTIMEROBOT) =================
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is alive"

def run_flask():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

threading.Thread(target=run_flask).start()

# ================= BOT =================
bot = telebot.TeleBot(TOKEN)

# ================= DATABASE =================
if not os.path.exists(DB_FILE):
    with open(DB_FILE, "w") as f:
        json.dump({"users": {}, "sponsors": []}, f)

def load_db():
    with open(DB_FILE, "r") as f:
        return json.load(f)

def save_db(db):
    with open(DB_FILE, "w") as f:
        json.dump(db, f, indent=2)

db = load_db()

def get_user(uid, username):
    uid = str(uid)
    if uid not in db["users"]:
        db["users"][uid] = {
            "id": uid,
            "username": username,
            "balance": 0,
            "refs": 0,
            "ref_by": None
        }
        save_db(db)
    return db["users"][uid]

# ================= KEYBOARDS =================
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
    kb.add("💰 Начислить Gram", "➖ Списать Gram")
    kb.add("📢 Рассылка")
    kb.add("🏠 Главное меню")
    return kb

# ================= START =================
@bot.message_handler(commands=["start"])
def start(m):
    user = get_user(m.from_user.id, m.from_user.username)
    ref = None
    if len(m.text.split()) > 1:
        ref = m.text.split()[1]
        if ref != str(m.from_user.id) and user["ref_by"] is None:
            user["ref_by"] = ref
            if ref in db["users"]:
                db["users"][ref]["refs"] += 1
                db["users"][ref]["balance"] += REF_REWARD
            save_db(db)

    text = (
        f"Привет, {m.from_user.first_name}!\n\n"
        "Ты в боте по заработку Gram.\n"
        "Приглашай друзей и зарабатывай!\n\n"
        "«Для начала подпишись на все каналы ниже 👇»"
    )

    ikb = types.InlineKeyboardMarkup()
    ikb.add(types.InlineKeyboardButton("📢 Новостник GramHub", url=f"https://t.me/{NEWS_CHANNEL.replace('@','')}"))

    for s in db["sponsors"]:
        ikb.add(types.InlineKeyboardButton("🔔 СПОНСОР", url=s))

    ikb.add(types.InlineKeyboardButton("✅ Проверить", callback_data="check"))

    bot.send_message(m.chat.id, text, reply_markup=ikb)

# ================= CHECK =================
@bot.callback_query_handler(func=lambda c: c.data == "check")
def check(c):
    uid = c.from_user.id
    ok = True

    for s in db["sponsors"]:
        try:
            member = bot.get_chat_member(s, uid)
            if member.status not in ["member", "administrator", "creator"]:
                ok = False
        except:
            ok = False

    if ok:
        bot.send_message(uid, "✅ Подписка подтверждена", reply_markup=main_menu(uid in ADMIN_IDS))
    else:
        bot.answer_callback_query(c.id, "❌ Подпишись на все каналы", show_alert=True)

# ================= USER MENU =================
@bot.message_handler(func=lambda m: m.text == "👤 Профиль")
def profile(m):
    u = db["users"][str(m.from_user.id)]
    text = (
        f"👤 Профиль\n\n"
        f"ID: {u['id']}\n"
        f"Рефералы: {u['refs']}\n"
        f"Баланс: {u['balance']} Gram"
    )
    bot.send_message(m.chat.id, text, reply_markup=main_menu(m.from_user.id in ADMIN_IDS))

@bot.message_handler(func=lambda m: m.text == "🤝 Пригласить")
def invite(m):
    link = f"https://t.me/{bot.get_me().username}?start={m.from_user.id}"
    text = (
        "🤝 Приглашай друзей и зарабатывай!\n\n"
        f"За 1 реферала — {REF_REWARD} Gram\n\n"
        "«Реферал считается после подписки»\n\n"
        f"Твоя ссылка:\n{link}"
    )
    bot.send_message(m.chat.id, text, reply_markup=main_menu(m.from_user.id in ADMIN_IDS))

@bot.message_handler(func=lambda m: m.text == "💸 Вывод Gram")
def withdraw(m):
    bal = db["users"][str(m.from_user.id)]["balance"]
    if bal < MIN_WITHDRAW:
        bot.send_message(m.chat.id, f"❌ Минимальный вывод {MIN_WITHDRAW} Gram", reply_markup=main_menu())
    else:
        bot.send_message(m.chat.id, "✏️ Введи сумму для вывода")

# ================= ADMIN =================
@bot.message_handler(func=lambda m: m.text == "🛠 Админка" and m.from_user.id in ADMIN_IDS)
def admin(m):
    bot.send_message(m.chat.id, "🛠 Админ-панель", reply_markup=admin_menu())

@bot.message_handler(func=lambda m: m.text == "🏠 Главное меню")
def back(m):
    bot.send_message(m.chat.id, "🏠 Главное меню", reply_markup=main_menu(m.from_user.id in ADMIN_IDS))

# ================= SPONSORS =================
@bot.message_handler(func=lambda m: m.text == "➕ Добавить спонсора" and m.from_user.id in ADMIN_IDS)
def add_s(m):
    bot.send_message(m.chat.id, "Отправь ссылку на канал")

    bot.register_next_step_handler(m, save_s)

def save_s(m):
    db["sponsors"].append(m.text)
    save_db(db)
    bot.send_message(m.chat.id, "✅ Спонсор добавлен", reply_markup=admin_menu())

@bot.message_handler(func=lambda m: m.text == "➖ Удалить спонсора" and m.from_user.id in ADMIN_IDS)
def rem_s(m):
    bot.send_message(m.chat.id, "Отправь ссылку для удаления")

    bot.register_next_step_handler(m, del_s)

def del_s(m):
    if m.text in db["sponsors"]:
        db["sponsors"].remove(m.text)
        save_db(db)
        bot.send_message(m.chat.id, "✅ Удалено", reply_markup=admin_menu())
    else:
        bot.send_message(m.chat.id, "❌ Не найдено", reply_markup=admin_menu())

# ================= BALANCE =================
@bot.message_handler(func=lambda m: m.text == "💰 Начислить Gram" and m.from_user.id in ADMIN_IDS)
def add_bal(m):
    bot.send_message(m.chat.id, "ID сумма")
    bot.register_next_step_handler(m, add_bal_do)

def add_bal_do(m):
    uid, amt = m.text.split()
    db["users"][uid]["balance"] += int(amt)
    save_db(db)
    bot.send_message(m.chat.id, "✅ Начислено", reply_markup=admin_menu())

@bot.message_handler(func=lambda m: m.text == "➖ Списать Gram" and m.from_user.id in ADMIN_IDS)
def sub_bal(m):
    bot.send_message(m.chat.id, "ID сумма")
    bot.register_next_step_handler(m, sub_bal_do)

def sub_bal_do(m):
    uid, amt = m.text.split()
    db["users"][uid]["balance"] -= int(amt)
    save_db(db)
    bot.send_message(m.chat.id, "✅ Списано", reply_markup=admin_menu())

# ================= BROADCAST =================
@bot.message_handler(func=lambda m: m.text == "📢 Рассылка" and m.from_user.id in ADMIN_IDS)
def bc(m):
    bot.send_message(m.chat.id, "Отправь текст рассылки")
    bot.register_next_step_handler(m, do_bc)

def do_bc(m):
    for uid in db["users"]:
        try:
            bot.send_message(uid, m.text)
        except:
            pass
    bot.send_message(m.chat.id, "✅ Рассылка отправлена", reply_markup=admin_menu())

# ================= RUN =================
print("Bot started")
bot.infinity_polling()
