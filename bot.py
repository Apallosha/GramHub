import telebot
from telebot import types
import random
from db import *  # сюда вынеси базу пользователей, спонсоров и функции работы с ними

TOKEN = "8275742360:AAFDN-FBvQtgdTNeCOd9nlWXJFXQS_4LbaU"
ADMIN_ID = 5333130126
NEWS_CHANNEL = "@GramHubNews"

REF_REWARD = 1250
MIN_WITHDRAW = 25000

bot = telebot.TeleBot(TOKEN)
bot.remove_webhook()  # удаляем старые вебхуки сразу после инициализации

captcha_cache = {}
withdraw_wait = set()

# ===== /start + капча =====
@bot.message_handler(commands=["start"])
def start(m):
    uid = m.from_user.id
    username = m.from_user.username or "Без ника"

    ref = None
    if len(m.text.split()) > 1:
        try:
            ref = int(m.text.split()[1])
        except:
            pass

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
        send_welcome(uid)
    else:
        bot.send_message(uid, "❌ Неверно, попробуй ещё")

# ===== Приветствие + спонсоры =====
def send_welcome(uid):
    username = bot.get_chat(uid).username or "Без ника"
    bot.send_message(uid,
        f"Привет {username}!\n"
        "Этот бот создан для заработка Gram.\n"
        "Приглашай друзей и зарабатывай!"
    )
    send_sponsors(uid)

def send_sponsors(uid):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("📰 Новостник", url=f"https://t.me/{NEWS_CHANNEL.replace('@','')}"))
    for s in get_sponsors():
        kb.add(types.InlineKeyboardButton("СПОНСОР", url=s))
    kb.add(types.InlineKeyboardButton("✅ Проверить", callback_data="check"))
    bot.send_message(uid, "Подпишись на всех спонсоров 👇", reply_markup=kb)

# ===== Проверка подписки =====
@bot.callback_query_handler(func=lambda c: c.data == "check")
def check_subs(c):
    uid = c.from_user.id
    for s in get_sponsors():
        try:
            chat = s.replace("https://t.me/","").replace("@","")
            status = bot.get_chat_member(chat, uid).status
            if status not in ["member","administrator","creator"]:
                bot.answer_callback_query(c.id, "❌ Ты не подписан на всех спонсоров", show_alert=True)
                return
        except:
            pass

    user = get_user(uid)
    if user and user[4]:  # invited_by
        ref_user = get_user(user[4])
        if ref_user:
            add_ref(user[4])
            add_balance(user[4], REF_REWARD)
            bot.send_message(ref_user[0], f"☘ У вас новый реферал - @{c.from_user.username}")

    main_menu(uid)

# ===== Главное меню =====
def main_menu(uid):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("👤 Профиль")
    kb.add("👥 Пригласить")
    kb.add("💸 Вывод Gram")
    bot.send_message(uid, "Главное меню", reply_markup=kb)

# ===== Профиль =====
@bot.message_handler(func=lambda m: m.text == "👤 Профиль")
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

# ===== Пригласить =====
@bot.message_handler(func=lambda m: m.text == "👥 Пригласить")
def invite(m):
    bot.send_message(
        m.chat.id,
        "Привет! Приглашай друзей в GramHub и зарабатывай по 1.250GRAM за одного реферала!\n\n"
        "> P.s реферал засчитывается только после подписки на всех спонсоров\n\n"
        f"Твоя реферальная ссылка:\n"
        f"https://t.me/{bot.get_me().username}?start={m.from_user.id}"
    )

# ===== Вывод Gram =====
@bot.message_handler(func=lambda m: m.text == "💸 Вывод Gram")
def withdraw(m):
    bal = get_user(m.from_user.id)[2]
    if bal < MIN_WITHDRAW:
        bot.send_message(m.chat.id,
            "❌ У тебя не достаточно Gram для вывода!\nМинимальный вывод 25.000 Gram!")
    else:
        withdraw_wait.add(m.from_user.id)
        bot.send_message(m.chat.id, "✍ Напиши сумму вывода Gram")

@bot.message_handler(func=lambda m: m.from_user.id in withdraw_wait)
def withdraw_sum(m):
    uid = m.from_user.id
    if not m.text.isdigit(): return
    amount = int(m.text)
    bal = get_user(uid)[2]
    if amount > bal:
        bot.send_message(uid, "❌ У тебя не достаточно Gram для вывода!")
    else:
        sub_balance(uid, amount)
        withdraw_wait.remove(uid)
        bot.send_message(uid,
            "Для вывода Gram выполни все по инструкции:\n"
            "1. Сделай скриншот с суммой вывода в боте!\n"
            "2. Зайди в группу: https://t.me/+5yNBdXSxMoMzMzVi\n"
            "3. Ожидай вывод в течении 48 часов, удачи ☘"
        )

# ===== Админка полностью =====
@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID)
def admin_panel(m):
    if m.text == "➕ Добавить спонсора":
        msg = bot.send_message(m.chat.id, "Пришли ссылку/username спонсора:")
        bot.register_next_step_handler(msg, lambda x: (add_sponsor(x.text.strip()), bot.send_message(m.chat.id, f"✅ Спонсор {x.text.strip()} добавлен!")))

    elif m.text == "➖ Удалить спонсора":
        msg = bot.send_message(m.chat.id, "Пришли ссылку/username для удаления:")
        bot.register_next_step_handler(msg, lambda x: (remove_sponsor(x.text.strip()), bot.send_message(m.chat.id, f"❌ Спонсор {x.text.strip()} удалён!")))

    elif m.text == "➕ Баланс":
        msg = bot.send_message(m.chat.id, "Пришли ID и сумму через пробел:")
        bot.register_next_step_handler(msg, lambda x: handle_balance(x, add=True))

    elif m.text == "➖ Баланс":
        msg = bot.send_message(m.chat.id, "Пришли ID и сумму через пробел:")
        bot.register_next_step_handler(msg, lambda x: handle_balance(x, add=False))

    elif m.text == "📢 Рассылка":
        msg = bot.send_message(m.chat.id, "Пришли текст рассылки:")
        bot.register_next_step_handler(msg, lambda x: broadcast(x.text))

def handle_balance(m, add=True):
    try:
        uid, amount = map(int, m.text.strip().split())
        if add:
            add_balance(uid, amount)
            bot.send_message(m.chat.id, f"✅ Баланс {uid} увеличен на {amount}")
        else:
            sub_balance(uid, amount)
            bot.send_message(m.chat.id, f"❌ Баланс {uid} уменьшен на {amount}")
    except:
        bot.send_message(m.chat.id, "❌ Ошибка! Формат: ID сумма")

def broadcast(text):
    for u in get_all_users():
        try:
            bot.send_message(u[0], text)
        except:
            continue

# ===== Запуск бота =====
def run_bot():
    bot.infinity_polling(skip_pending=True)
