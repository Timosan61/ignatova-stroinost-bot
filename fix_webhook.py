#!/usr/bin/env python3
"""
Исправление webhook URL для бота
"""
import os
import requests
import json

# Получаем токен
token = os.getenv('TELEGRAM_BOT_TOKEN')
if not token:
    try:
        with open('.env', 'r') as f:
            for line in f:
                if line.startswith('TELEGRAM_BOT_TOKEN='):
                    token = line.split('=', 1)[1].strip().strip('"')
                    break
    except:
        pass

if not token:
    print("❌ TELEGRAM_BOT_TOKEN не найден")
    exit(1)

print(f"🔑 Токен найден: {token[:20]}...")

# Сначала удаляем старый webhook
print("\n🗑️ Удаляем старый webhook...")
delete_url = f'https://api.telegram.org/bot{token}/deleteWebhook'
try:
    response = requests.post(delete_url, timeout=10)
    data = response.json()
    if data.get('ok'):
        print("✅ Старый webhook удален")
    else:
        print(f"⚠️ Ошибка удаления: {data}")
except Exception as e:
    print(f"❌ Ошибка: {e}")

# Проверяем доступные URL варианты
possible_urls = [
    "https://ignatova-stroinost-bot-production.up.railway.app/webhook",
    "https://web-production-f742.up.railway.app/webhook",  # Альтернативный Railway URL
    "https://production-service.up.railway.app/webhook"    # Еще один вариант
]

print("\n🔍 Проверяем доступность URL...")
working_url = None

for url in possible_urls:
    base_url = url.replace('/webhook', '')
    try:
        print(f"   Проверяем: {base_url}")
        response = requests.get(base_url, timeout=5)
        print(f"   Статус: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                if 'status' in data and 'bot' in data:
                    print(f"   ✅ РАБОТАЕТ! Bot: {data.get('bot', 'N/A')}")
                    working_url = url
                    break
            except:
                pass
    except Exception as e:
        print(f"   ❌ Недоступен: {e}")

if not working_url:
    print("\n❌ НИ ОДИН URL НЕ РАБОТАЕТ!")
    print("Проблема с Railway deployment. Проверьте логи Railway.")
    exit(1)

print(f"\n✅ Рабочий URL найден: {working_url}")

# Устанавливаем новый webhook
print(f"\n🔧 Устанавливаем webhook: {working_url}")
set_url = f'https://api.telegram.org/bot{token}/setWebhook'
webhook_data = {
    'url': working_url,
    'allowed_updates': ['message', 'edited_message', 'callback_query'],
    'drop_pending_updates': True  # Очищаем накопившиеся сообщения
}

try:
    response = requests.post(set_url, json=webhook_data, timeout=10)
    data = response.json()
    
    if data.get('ok'):
        print("✅ Webhook успешно установлен!")
        print(f"   URL: {working_url}")
        print("   ✅ Очищены накопившиеся сообщения")
        print("   📱 Теперь отправьте сообщение боту для проверки")
    else:
        print(f"❌ Ошибка установки webhook: {data}")
except Exception as e:
    print(f"❌ Ошибка: {e}")

print("\n" + "="*50)
print("💡 СЛЕДУЮЩИЕ ШАГИ:")
print("1. Отправьте сообщение боту")
print("2. Проверьте логи Railway - должны появиться записи о webhook")
print("3. Если не работает - возможно Railway URL изменился")