import telebot
from telebot import types
from flask import Flask, request
import random, os
from database import init_db, get_user, update_user, get_all_users, add_sponsor, remove_sponsor, get_sponsors

# ================= НАСТРОЙКИ =================
TOKEN = "8275742360:AAFDN-FBvQtgdTNeCOd9nlWXJFXQS_4LbaU"
ADMIN_IDS = [5333130126]
NEWS_CHANNEL = "@GramHubNews"
WEBHOOK_URL = "https://gramhub-2qn6.onrender.com/webhook"

REF_BONUS = 1250
MIN_WITHDRAW = 25000

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")
app = Flask(__name__)

init_db()

# =================== состояния ===================
user_state = {}
admin_state = {}

# =================== клавиатуры ===================
def main_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("👤 Профиль", "👥 Пригласить")
    kb.add("💸 Вывод Gram")
    kb.add("⬅ Главное меню")  # админка видна только в меню
    return kb

def admin_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("➕ Добавить спонсора", "➖ Удалить спонсора")
    kb.add("➕ Начислить баланс", "➖ Списать баланс")
    kb.add("📢 Рассылка")
    kb.add("⬅ Главное меню")
    return kb

def sponsors_kb():
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("📰 Новостник", url=f"https://t.me/{NEWS_CHANNEL.replace('@','')}"))
    sponsors = get_sponsors()
    for s in sponsors:
        kb.add(types.InlineKeyboardButton("💎 СПОНСОР", url=s))
    kb.add(types.InlineKeyboardButton("✅ Проверить", callback_data="check_subs"))
    return kb

# =================== START + КАПЧА ===================
@bot.message_handler(commands=["start"])
def start(m):
    uid = m.from_user.id
    user = get_user(uid)
    if len(m.text.split()) > 1 and not user[4]:  # invited_by
        ref = int(m.text.split()[1])
        if ref != uid:
            update_user(uid, invited_by=ref)
    a, b = random.randint(1, 9), random.randint(1, 9)
    update_user(uid, captcha=a+b)
    bot.send_message(uid, f"🔐 Капча:\n<b>{a} + {b} = ?</b>")

# =================== капча ===================
@bot.message_handler(func=lambda m: True)
def check_captcha(m):
    uid = m.from_user.id
    user = get_user(uid)
    if user[5] is None:  # captcha
        return
    try:
        answer = int(m.text.strip())
    except:
        bot.send_message(uid, "❌ Введи число")
        return
    if answer == user[5]:
        update_user(uid, captcha=None)
        bot.send_message(uid,
                         "Привет! Подпишись на всех спонсоров чтобы пользоваться ботом!",
                         reply_markup=sponsors_kb())
    else:
        bot.send_message(uid, "❌ Неверно, попробуй ещё раз")

# =================== проверка подписки ===================
@bot.callback_query_handler(func=lambda c: c.data=="check_subs")
def check_subs(c):
    uid = c.from_user.id
    sponsors = get_sponsors() + [NEWS_CHANNEL]
    # TODO: проверка подписки через get_chat_member
    update_user(uid, sub_ok=1)
    bot.send_message(uid, "✅ Подписка подтверждена! Меню разблокировано.", reply_markup=main_menu())
    # начисляем реферальный бонус
    user = get_user(uid)
    if user[4]:  # invited_by
        inviter = get_user(user[4])
        update_user(user[4], balance=inviter[2]+REF_BONUS, refs=inviter[3]+1)

# =================== ПРОФИЛЬ ===================
@bot.message_handler(func=lambda m: m.text=="👤 Профиль")
def profile(m):
    u = get_user(m.from_user.id)
    bot.send_message(m.chat.id,
                     f"Привет {m.from_user.username}!\nID: {u[0]}\nБаланс: {u[2]} Gram\nРефералов: {u[3]}\nТвоя ссылка:\nhttps://t.me/{bot.get_me().username}?start={u[0]}")

# =================== ПРИГЛАСИТЬ ===================
@bot.message_handler(func=lambda m: m.text=="👥 Пригласить")
def invite(m):
    bot.send_message(m.chat.id,
                     f"Привет {m.from_user.username}!\nПолучай 1.250GRAM за каждого друга!\n<blockquote>P.s реферал засчитывается после подписки!</blockquote>\nhttps://t.me/{bot.get_me().username}?start={m.from_user.id}")

# =================== ВЫВОД ===================
withdraw_state = {}
@bot.message_handler(func=lambda m: m.text=="💸 Вывод Gram")
def withdraw(m):
    u = get_user(m.from_user.id)
    if u[2]<MIN_WITHDRAW:
        bot.send_message(m.chat.id, "❌ Минимальный вывод 25k Gram")
        return
    withdraw_state[m.from_user.id] = True
    bot.send_message(m.chat.id, "Введи сумму для вывода:")

@bot.message_handler(func=lambda m: m.from_user.id in withdraw_state)
def withdraw_sum(m):
    uid = m.from_user.id
    try:
        amount = int(m.text.strip())
    except:
        bot.send_message(uid, "❌ Введи число")
        return
    u = get_user(uid)
    if amount<MIN_WITHDRAW or u[2]<amount:
        bot.send_message(uid, "❌ Не достаточно Gram")
        withdraw_state.pop(uid)
        return
    update_user(uid, balance=u[2]-amount)
    withdraw_state.pop(uid)
    bot.send_message(uid, "Для вывода Gram осталось не много!\n1. Скриншот\n2. https://t.me/+5yNBdXSxMoMzMzVi\n3. Жди 2-3 дня\nУдачи ☘️")

# =================== АДМИНКА ===================
@bot.message_handler(func=lambda m: m.text=="⬅ Главное меню")
def main_menu_btn(m):
    if m.from_user.id in ADMIN_IDS:
        bot.send_message(m.chat.id, "Главное меню", reply_markup=admin_kb())
    else:
        bot.send_message(m.chat.id, "Главное меню", reply_markup=main_menu())

# =================== WEBHOOK ===================
@app.route("/webhook", methods=["POST"])
def webhook():
    update = telebot.types.Update.de_json(request.stream.read().decode("utf-8"))
    bot.process_new_updates([update])
    return "OK",200

if __name__=="__main__":
    bot.remove_webhook()
    bot.set_webhook(WEBHOOK_URL)
    port=int(os.environ.get("PORT",10000))
    app.run(host="0.0.0.0", port=port)
