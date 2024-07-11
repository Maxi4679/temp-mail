# Автор (C) @theSmartBisnu
# Канал: https://t.me/itsSmartDev

import hashlib
import time
import re
import requests
import random
import string
from bs4 import BeautifulSoup
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.contrib.fsm_storage.memory import MemoryStorage

# Инициализация бота и диспетчера
API_TOKEN = ''  # Измените токен на токен вашего бота
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Словарь для хранения данных пользовательских запросов
user_data = {}

# Словарь для хранения токенов с короткими идентификаторами
token_map = {}

# Для функции чтения почты
user_tokens = {}
MAX_MESSAGE_LENGTH = 4000

BASE_URL = "https://api.mail.tm"
HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json"
}

def short_id_generator(email):
    """Генерирует короткий ID на основе email и текущего времени."""
    unique_string = email + str(time.time())
    return hashlib.md5(unique_string.encode()).hexdigest()[:10]  # Возвращает первые 10 символов MD5 хеша

def generate_random_username(length=8):
    """Генерирует случайное имя пользователя заданной длины."""
    return ''.join(random.choice(string.ascii_lowercase) for i in range(length))

def generate_random_password(length=12):
    """Генерирует случайный пароль заданной длины."""
    characters = string.ascii_letters + string.digits + string.punctuation
    return ''.join(random.choice(characters) for i in range(length))

def get_domain():
    """Получает доступный домен для временной почты."""
    response = requests.get(f"{BASE_URL}/domains", headers=HEADERS)
    data = response.json()
    if isinstance(data, list) and data:
        return data[0]['domain']
    elif 'hydra:member' in data and data['hydra:member']:
        return data['hydra:member'][0]['domain']
    return None

def create_account(email, password):
    """Создает новый аккаунт временной почты."""
    data = {
        "address": email,
        "password": password
    }
    response = requests.post(f"{BASE_URL}/accounts", headers=HEADERS, json=data)
    if response.status_code in [200, 201]:
        return response.json()
    else:
        print(f"Код ошибки: {response.status_code}")
        print(f"Ответ: {response.text}")
        return None

def get_token(email, password):
    """Получает токен для аутентификации."""
    data = {
        "address": email,
        "password": password
    }
    response = requests.post(f"{BASE_URL}/token", headers=HEADERS, json=data)
    if response.status_code == 200:
        return response.json().get('token')
    else:
        print(f"Код ошибки токена: {response.status_code}")
        print(f"Ответ токена: {response.text}")
        return None

def get_text_from_html(html_content_list):
    """Извлекает текст из HTML-содержимого."""
    html_content = ''.join(html_content_list)
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Извлекаем URL из тегов anchor и добавляем их к тексту anchor
    for a_tag in soup.find_all('a', href=True):
        url = a_tag['href']
        new_content = f"{a_tag.text} [{url}]"
        a_tag.string = new_content

    text_content = soup.get_text()
    cleaned_content = re.sub(r'\s+', ' ', text_content).strip()
    return cleaned_content

def list_messages(token):
    """Получает список сообщений для данного токена."""
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {token}"
    }
    response = requests.get(f"{BASE_URL}/messages", headers=headers)
    data = response.json()
    if isinstance(data, list):
        return data
    elif 'hydra:member' in data:
        return data['hydra:member']
    else:
        return []

@dp.message_handler(commands=['tmail'])  # Вы можете изменить команду tmail
async def generate_mail(message: types.Message):
    if message.chat.type != 'private':
        await bot.send_message(message.chat.id, "<b>❌ Бро, функция TempMail работает только в приватном чате, потому что это личное.</b>", parse_mode="html")
        return

    if not message.text.startswith(('/tmail', '.tmail')):
        return

    loading_msg = await message.answer("<b>Генерирую вашу временную почту...</b>", parse_mode='html')

    args_text = ""
    if message.text.startswith('/tmail'):
        args_text = message.get_args()
    elif message.text.startswith('.tmail'):
        args_text = message.text.replace('.tmail', '').strip()

    args = args_text.split()
    if len(args) == 1 and ':' in args[0]:
        username, password = args[0].split(':')
    else:
        username = generate_random_username()
        password = generate_random_password()

    domain = get_domain()
    if not domain:
        await message.answer("<b>Не удалось получить домен, попробуйте еще раз</b>", parse_mode='html')
        await bot.delete_message(chat_id=message.chat.id, message_id=loading_msg.message_id)
        return

    email = f"{username}@{domain}"
    account = create_account(email, password)
    if not account:
        await message.answer("<b>Имя пользователя уже занято. Выберите другое.</b>", parse_mode='html')
        await bot.delete_message(chat_id=message.chat.id, message_id=loading_msg.message_id)
        return

    time.sleep(2)

    token = get_token(email, password)
    if not token:
        await message.answer("<b>Не удалось получить токен.</b>", parse_mode='html')
        await bot.delete_message(chat_id=message.chat.id, message_id=loading_msg.message_id)
        return

    # Вместо передачи полного токена, генерируем короткий id
    short_id = short_id_generator(email)
    token_map[short_id] = token  # Сопоставляем короткий ID с токеном

    output_message = (
        "<b>📧 Детали Smart-Email 📧</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"📧 Email: <code>{email}</code>\n"
        f"🔑 Пароль: <code>{password}</code>\n"
        f"🔒 Токен: <code>{token}</code>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "<b>Примечание: Сохраните токен для доступа к почте</b>"
    )

    keyboard = InlineKeyboardMarkup()
    button = InlineKeyboardButton("Проверить почту", callback_data=f"check_{short_id}")
    keyboard.add(button)

    await message.answer(output_message, reply_markup=keyboard, parse_mode='html')
    await bot.delete_message(chat_id=message.chat.id, message_id=loading_msg.message_id)

@dp.callback_query_handler(lambda c: c.data.startswith('check_'))
async def check_mail(callback_query: types.CallbackQuery):
    short_id = callback_query.data.split('_')[1]
    token = token_map.get(short_id)
    if not token:
        await callback_query.message.answer("Сессия истекла, пожалуйста, используйте /cmail с вашим токеном.")
        return

    # Сохраняем токен в словаре user_tokens для последующего использования в read_message
    user_tokens[callback_query.from_user.id] = token

    # Отправляем сообщение о загрузке
    loading_msg = await callback_query.message.answer("<code>⏳ Проверяю почту.. Пожалуйста, подождите.</code>", parse_mode='html')

    messages = list_messages(token)
    if not messages:
        await callback_query.message.answer("<b>❌ Сообщений не найдено. Возможно, неверный токен или нет новых сообщений.</b>", parse_mode='html')
        await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=loading_msg.message_id)  # Удаляем сообщение о загрузке
        return

    output = "📧 <b>Ваши сообщения Smart-Mail</b> 📧\n"
    output += "━━━━━━━━━━━━━━━━━━\n"
    
    keyboard = InlineKeyboardMarkup(row_width=5)
    buttons = []
    for idx, msg in enumerate(messages[:10], 1):
        output += f"<b>{idx}. От: <code>{msg['from']['address']}</code> - Тема: {msg['subject']}</b>\n"
        button = InlineKeyboardButton(f"{idx}", callback_data=f"read_{msg['id']}")
        buttons.append(button)
    
    for i in range(0, len(buttons), 5):
        keyboard.row(*buttons[i:i+5])

    await callback_query.message.answer(output, reply_markup=keyboard, parse_mode='html')
    await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=loading_msg.message_id)  # Удаляем сообщение о загрузке

@dp.message_handler(commands=['cmail']) # Вы можете изменить команду cmail
async def manual_check_mail(message: types.Message):
    # Проверяем, является ли тип чата приватным
    if message.chat.type != 'private':
        await bot.send_message(message.chat.id, "<b>❌ Бро, функция TempMail работает только в приватном чате</b>", parse_mode="html")
        return

    # Отправляем сообщение о загрузке
    loading_msg = await bot.send_message(message.chat.id, "<code>⏳ Проверяю почту.. Пожалуйста, подождите.</code>", parse_mode='html')

    token = message.get_args()
    if not token:
        await message.answer("<b>Пожалуйста, укажите токен после команды /cmail.</b>", parse_mode='html')
        await bot.delete_message(chat_id=message.chat.id, message_id=loading_msg.message_id)  # Удаляем сообщение о загрузке
        return

    user_tokens[message.from_user.id] = token
    messages = list_messages(token)
    if not messages:
        await message.answer("<b>❌ Сообщений не найдено, возможно, неверный токен</b>", parse_mode='html')
        await bot.delete_message(chat_id=message.chat.id, message_id=loading_msg.message_id)  # Удаляем сообщение о загрузке
        return

    output = "📧 <b>Ваши сообщения Smart-Mail</b> 📧\n"
    output += "━━━━━━━━━━━━━━━━━━\n"
    
    keyboard = InlineKeyboardMarkup(row_width=5)
    buttons = []
    for idx, msg in enumerate(messages[:10], 1):
        output += f"<b>{idx}. От: <code>{msg['from']['address']}</code> - Тема: {msg['subject']}</b>\n"
        button = InlineKeyboardButton(f"{idx}", callback_data=f"read_{msg['id']}")
        buttons.append(button)
    
    for i in range(0, len(buttons), 5):
        keyboard.row(*buttons[i:i+5])

    await message.answer(output, reply_markup=keyboard, parse_mode='html')
    await bot.delete_message(chat_id=message.chat.id, message_id=loading_msg.message_id)  # Удаляем сообщение о загрузке

@dp.callback_query_handler(lambda c: c.data.startswith('read_'))
async def read_message(callback_query: types.CallbackQuery):   
    _, message_id = callback_query.data.split('_')
    
    token = user_tokens.get(callback_query.from_user.id)
    if not token:
        await bot.send_message(callback_query.message.chat.id, "Токен не найден. Пожалуйста, используйте /cmail с вашим токеном снова.")
        return

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {token}"
    }
    response = requests.get(f"{BASE_URL}/messages/{message_id}", headers=headers)
    
    if response.status_code == 200:
        details = response.json()
        if 'html' in details:
            message_text = get_text_from_html(details['html'])
        elif 'text' in details:
            message_text = details['text']
        else:
            message_text = "Содержимое недоступно."
        
        # Проверяем, не превышает ли длина сообщения максимально допустимую в Telegram
        if len(message_text) > MAX_MESSAGE_LENGTH:
            message_text = message_text[:MAX_MESSAGE_LENGTH - 100] + "... [message truncated]"

@dp.callback_query_handler(lambda c: c.data.startswith('read_'))
async def read_message(callback_query: types.CallbackQuery):   
    _, message_id = callback_query.data.split('_')
    
    token = user_tokens.get(callback_query.from_user.id)
    if not token:
        await bot.send_message(callback_query.message.chat.id, "Токен не найден. Пожалуйста, используйте /cmail с вашим токеном снова.")
        return

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {token}"
    }
    response = requests.get(f"{BASE_URL}/messages/{message_id}", headers=headers)
    
    if response.status_code == 200:
        details = response.json()
        if 'html' in details:
            message_text = get_text_from_html(details['html'])
        elif 'text' in details:
            message_text = details['text']
        else:
            message_text = "Содержимое недоступно."
        
        # Проверяем, не превышает ли длина сообщения максимально допустимую в Telegram
        if len(message_text) > MAX_MESSAGE_LENGTH:
            message_text = message_text[:MAX_MESSAGE_LENGTH - 100] + "... [сообщение обрезано]"

        output = f"От: {details['from']['address']}\nТема: {details['subject']}\n━━━━━━━━━━━━━━━━━━\n{message_text}"
        await bot.send_message(callback_query.message.chat.id, output, disable_web_page_preview=True)
    else:
        await bot.send_message(callback_query.message.chat.id, "Ошибка при получении деталей сообщения.")

# Запуск бота
if __name__ == '__main__':
    from aiogram import executor
    executor.start_polling(dp, skip_updates=True)
