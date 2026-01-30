import telebot
import random
from telebot import types
from db import *

TOKEN = "8275742360:AAFDN-FBvQtgdTNeCOd9nlWXJFXQS_4LbaU"
ADMIN_ID = 5333130126   # твой ID
NEWS_CHANNEL = "@GramHubNews"

REF_REWARD = 1250
MIN_WITHDRAW = 25000

bot = telebot.TeleBot(TOKEN)
bot.remove_webhook()

captcha_cache = {}
withdraw_wait = set()
admin_state = {}

# ===== START + CAPTCHA =====
@bot.message_handler(commands=["start"])
def start(m):
    uid = m.from_user.id
    username = m.from_user.username or "Без ника"

    ref = None
    if len(m.text.split()) > 1:
        ref = int(m.text.split()[1])

    add_user(uid, username, ref)

    a = random.randint(1,5)
    b = random.randint(1,5)
    sign = random.choice(["+","-"])
    ans = a + b if sign == "+" else a - b
    captcha_cache[uid] = ans

    bot.send_message(uid, f"🤖 Капча: {a} {sign} {b} = ?")

@bot.message_handler(func=lambda m: m.from_user.id in captcha_cache)
def captcha_check(m):
    uid = m.from_user.id
    if m.text.strip() == str(captcha_cache[uid]):
        del captcha_cache[uid]
        send_sponsors(uid)
    else:
        bot.send_message(uid, "❌ Неверно, попробуй ещё")

# ===== SPONSORS =====
def send_sponsors(uid):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("📰 Новостник", url=f"https://t.me/{NEWS_CHANNEL.replace('@','')}"))

    for s in get_sponsors():
        kb.add(types.InlineKeyboardButton("СПОНСОР", url=s))

    kb.add(types.InlineKeyboardButton("✅ Проверить", callback_data="check"))
    bot.send_message(uid, "Подпишись на всех спонсоров 👇", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data == "check")
def check_subs(c):
    uid = c.from_user.id

    for s in get_sponsors():
        try:
            chat = s.replace("https://t.me/","").replace("@","")
            status = bot.get_chat_member(chat, uid).status
            if status not in ["member","administrator","creator"]:
                bot.answer_callback_query(c.id, "❌ Ты не подписан", show_alert=True)
                return
        except:
            pass

    user = get_user(uid)
    if user and user[4]:
        ref_user = get_user(user[4])
        if ref_user:
            add_ref(user[4])
            add_balance(user[4], REF_REWARD)
            bot.send_message(
                user[4],
                f"☘ У вас новый реферал - @{c.from_user.username}"
            )

    main_menu(uid)

# ===== MAIN MENU =====
def main_menu(uid):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("👤 Профиль")
    kb.add("👥 Пригласить")
    kb.add("💸 Вывод Gram")

    bot.send_message(
        uid,
        f"Привет {bot.get_chat(uid).username}!\n"
        "Этот бот создан для заработка Gram.\n"
        "Приглашай друзей и зарабатывай!",
        reply_markup=kb
    )

# ===== PROFILE =====
@bot.message_handler(text="👤 Профиль")
def profile(m):
    u = get_user(m.from_user.id)
    bot.send_message(
        m.chat.id,
        f"Привет {m.from_user.username}!\n\n"
        f"ID: {u[0]}\n"
        f"Баланс: {u[2]} Gram\n"
        f"Рефералов: {u[3]}\n"
        f"Твоя реферальная ссылка:\n"
        f"https://t.me/{bot.get_me().username}?start={u[0]}"
    )

# ===== INVITE =====
@bot.message_handler(text="👥 Пригласить")
def invite(m):
    bot.send_message(
        m.chat.id,
        "Привет! Приглашай друзей в GramHub и зарабатывай по 1.250GRAM за одного реферала!\n\n"
        "> P.s реферал засчитывается только после подписки на всех спонсоров\n\n"
        f"Твоя реферальная ссылка:\n"
        f"https://t.me/{bot.get_me().username}?start={m.from_user.id}",
        parse_mode="Markdown"
    )

# ===== WITHDRAW =====
@bot.message_handler(text="💸 Вывод Gram")
def withdraw(m):
    bal = get_user(m.from_user.id)[2]
    if bal < MIN_WITHDRAW:
        bot.send_message(
            m.chat.id,
            "❌ У тебя не достаточно Gram для вывода!\n"
            "Минимальный вывод 25.000 Gram!"
        )
    else:
        withdraw_wait.add(m.from_user.id)
        bot.send_message(m.chat.id, "✍ Напиши сумму вывода Gram")

@bot.message_handler(func=lambda m: m.from_user.id in withdraw_wait)
def withdraw_sum(m):
    uid = m.from_user.id
    if not m.text.isdigit():
        return

    amount = int(m.text)
    bal = get_user(uid)[2]

    if amount > bal:
        bot.send_message(uid, "❌ У тебя не достаточно Gram для вывода!")
    else:
        sub_balance(uid, amount)
        withdraw_wait.remove(uid)
        bot.send_message(
            uid,
            "Для вывода Gram выполни все по инструкции:\n"
            "1. Сделай скриншот с суммой вывода в боте!\n"
            "2. Зайди в группу: https://t.me/+5yNBdXSxMoMzMzVi\n"
            "3. Ожидай вывод в течении 48 часов, удачи ☘"
        )

# ===== ADMIN =====
@bot.message_handler(commands=["admin"])
def admin(m):
    if m.from_user.id != ADMIN_ID:
        return

    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("➕ Добавить спонсора", "➖ Удалить спонсора")
    kb.add("➕ Баланс", "➖ Баланс")
    kb.add("📢 Рассылка")
    bot.send_message(m.chat.id, "Админ панель", reply_markup=kb)

# (логика админ-действий можно расширять — база готова)

def run_bot():
    bot.infinity_polling(skip_pending=True)
