#!/usr/bin/env python3
"""
Тестирование различных способов отправки через Business API
"""

import telebot
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '7902755829:AAH-WUhXSYq8NckAjFb22E-4D1O7ix_kzPM')
bot = telebot.TeleBot(BOT_TOKEN)

# Данные из вашего debug вывода
CHAT_ID = 5691290170  # Мультипарк
BUSINESS_CONNECTION_ID = "nQ3aLd_8oEodCQAA6DR5Or2GAHI"

print("🧪 Тестирование Business API отправки")
print("=" * 50)

# Тест 1: Стандартная отправка с business_connection_id
print("\n1️⃣ Тест: Отправка с business_connection_id")
try:
    result = bot.send_message(
        chat_id=CHAT_ID,
        text="🧪 Тест 1: Сообщение через Business API",
        business_connection_id=BUSINESS_CONNECTION_ID
    )
    print(f"✅ Успешно! Message ID: {result.message_id}")
except Exception as e:
    print(f"❌ Ошибка: {e}")

# Тест 2: Отправка как обычное сообщение
print("\n2️⃣ Тест: Обычная отправка без business_connection_id")
try:
    result = bot.send_message(
        chat_id=CHAT_ID,
        text="🧪 Тест 2: Обычное сообщение (не Business API)"
    )
    print(f"✅ Успешно! Message ID: {result.message_id}")
except Exception as e:
    print(f"❌ Ошибка: {e}")

# Тест 3: Использование reply_parameters
print("\n3️⃣ Тест: Отправка с reply_parameters")
try:
    from telebot.types import ReplyParameters
    reply_params = ReplyParameters(
        message_id=96074,  # ID из business_message
        chat_id=CHAT_ID
    )
    result = bot.send_message(
        chat_id=CHAT_ID,
        text="🧪 Тест 3: Ответ через reply_parameters",
        reply_parameters=reply_params
    )
    print(f"✅ Успешно! Message ID: {result.message_id}")
except Exception as e:
    print(f"❌ Ошибка: {e}")

# Тест 4: Raw API запрос
print("\n4️⃣ Тест: Raw API запрос")
try:
    import requests
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": "🧪 Тест 4: Raw API с business_connection_id",
        "business_connection_id": BUSINESS_CONNECTION_ID
    }
    
    response = requests.post(url, json=data)
    result = response.json()
    
    if result.get("ok"):
        print(f"✅ Успешно! Response: {result}")
    else:
        print(f"❌ Ошибка API: {result}")
        
except Exception as e:
    print(f"❌ Ошибка: {e}")

print("\n" + "=" * 50)
print("✅ Тестирование завершено!")
print("\nЕсли какой-то из тестов сработал, используйте этот метод в боте.")