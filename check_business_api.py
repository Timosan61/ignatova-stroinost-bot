#!/usr/bin/env python3
"""
🔍 Скрипт диагностики Telegram Business API
Проверяет настройки и работоспособность Business API
"""

import os
import sys
import json
import telebot
import requests
from datetime import datetime

# Загружаем переменные окружения
from dotenv import load_dotenv
load_dotenv()

# Получаем токен бота
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '7902755829:AAH-WUhXSYq8NckAjFb22E-4D1O7ix_kzPM')
WEBHOOK_URL = "https://bot-production-472c.up.railway.app/webhook"

print("=" * 60)
print("🔍 ДИАГНОСТИКА TELEGRAM BUSINESS API")
print("=" * 60)

# Создаем бота
bot = telebot.TeleBot(BOT_TOKEN)

# 1. Проверка информации о боте
print("\n1️⃣ ИНФОРМАЦИЯ О БОТЕ:")
try:
    bot_info = bot.get_me()
    print(f"✅ Бот: @{bot_info.username}")
    print(f"📊 ID: {bot_info.id}")
    print(f"📛 Имя: {bot_info.first_name}")
    print(f"🤖 Это бот: {bot_info.is_bot}")
    print(f"💼 Поддержка Business: {bot_info.can_join_groups}")
    print(f"📝 Может читать все сообщения: {bot_info.can_read_all_group_messages if hasattr(bot_info, 'can_read_all_group_messages') else 'N/A'}")
except Exception as e:
    print(f"❌ Ошибка получения информации о боте: {e}")

# 2. Проверка webhook
print("\n2️⃣ ПРОВЕРКА WEBHOOK:")
try:
    webhook_info = bot.get_webhook_info()
    print(f"📍 URL: {webhook_info.url or '❌ Не установлен'}")
    print(f"📊 Pending updates: {webhook_info.pending_update_count}")
    print(f"⚠️ Последняя ошибка: {webhook_info.last_error_message or '✅ Нет ошибок'}")
    print(f"🕐 Последняя ошибка (время): {webhook_info.last_error_date or 'Никогда'}")
    print(f"🔒 Кастомный сертификат: {webhook_info.has_custom_certificate}")
    print(f"📋 Разрешенные updates: {webhook_info.allowed_updates or 'Все'}")
    
    # Проверяем наличие business updates
    if webhook_info.allowed_updates:
        business_updates = [u for u in webhook_info.allowed_updates if 'business' in u]
        if business_updates:
            print(f"✅ Business updates включены: {business_updates}")
        else:
            print("❌ Business updates НЕ включены!")
    
except Exception as e:
    print(f"❌ Ошибка проверки webhook: {e}")

# 3. Проверка прав бота через API
print("\n3️⃣ ПРОВЕРКА ПРАВ БОТА:")
try:
    # Пробуем получить business_connection через getUpdates (для теста)
    updates = bot.get_updates(limit=5, timeout=1)
    print(f"📨 Получено {len(updates)} последних updates")
    
    for update in updates:
        if hasattr(update, 'business_connection'):
            print(f"✅ Найден business_connection!")
            bc = update.business_connection
            print(f"   - ID: {bc.id}")
            print(f"   - Пользователь: {bc.user.first_name}")
            print(f"   - Включен: {bc.is_enabled}")
            print(f"   - Дата: {bc.date}")
            
        if hasattr(update, 'business_message'):
            print(f"✅ Найден business_message!")
            bm = update.business_message
            print(f"   - Chat ID: {bm.chat.id}")
            print(f"   - От: {bm.from_user.first_name}")
            print(f"   - Connection ID: {getattr(bm, 'business_connection_id', 'НЕТ')}")
            
except Exception as e:
    print(f"⚠️ Не удалось получить updates (это нормально для webhook): {e}")

# 4. Тест отправки через Business API
print("\n4️⃣ ТЕСТ ОТПРАВКИ ЧЕРЕЗ BUSINESS API:")
print("⚠️ Для этого теста нужен реальный business_connection_id")
print("💡 Совет: Проверьте логи Railway после того, как клиент напишет вам")

# 5. Проверка Railway endpoint
print("\n5️⃣ ПРОВЕРКА RAILWAY ENDPOINT:")
try:
    response = requests.get("https://bot-production-472c.up.railway.app/", timeout=5)
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Сервер доступен: {data.get('status', 'Unknown')}")
        print(f"🤖 AI статус: {data.get('ai_status', 'Unknown')}")
        print(f"🔗 Режим: {data.get('mode', 'Unknown')}")
    else:
        print(f"❌ Сервер вернул код: {response.status_code}")
except Exception as e:
    print(f"❌ Ошибка подключения к серверу: {e}")

# 6. Рекомендации
print("\n6️⃣ РЕКОМЕНДАЦИИ:")
print("1. Убедитесь, что в настройках Telegram:")
print("   - Settings → Business → Chatbots → выбран ваш бот")
print("   - Бот имеет разрешение отвечать на сообщения")
print("\n2. Проверьте логи Railway после отправки тестового сообщения")
print("   - Должен появиться business_message")
print("   - Проверьте значение business_connection_id")
print("\n3. Если business_message не приходит:")
print("   - Переподключите бота в настройках Business")
print("   - Проверьте, что у вас активна подписка Telegram Premium")

print("\n" + "=" * 60)
print("✅ Диагностика завершена!")
print("=" * 60)

# 7. Интерактивный тест
print("\n7️⃣ ИНТЕРАКТИВНЫЙ ТЕСТ:")
print("Хотите попробовать отправить тестовое сообщение? (y/n)")
answer = input().lower()

if answer == 'y':
    chat_id = input("Введите chat_id для теста: ")
    connection_id = input("Введите business_connection_id (или Enter для пропуска): ")
    
    try:
        if connection_id:
            bot.send_message(
                chat_id=chat_id,
                text="🧪 Тестовое сообщение через Business API",
                business_connection_id=connection_id
            )
            print("✅ Сообщение отправлено через Business API!")
        else:
            bot.send_message(chat_id, "🧪 Тестовое обычное сообщение")
            print("✅ Обычное сообщение отправлено!")
    except Exception as e:
        print(f"❌ Ошибка отправки: {e}")