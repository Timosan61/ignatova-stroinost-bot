#!/usr/bin/env python3
"""
Установка правильного webhook URL для Railway
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

# Правильный внешний URL Railway 
# Формат: https://[service-name].up.railway.app
webhook_url = "https://ignatova-stroinost-bot.up.railway.app/webhook"

print(f"\n🔧 Устанавливаем webhook: {webhook_url}")

# Сначала проверим доступность URL
print("🔍 Проверяем доступность URL...")
base_url = webhook_url.replace('/webhook', '')

try:
    response = requests.get(base_url, timeout=10)
    print(f"Статус: {response.status_code}")
    
    if response.status_code == 200:
        try:
            data = response.json()
            print(f"✅ URL работает! Bot: {data.get('bot', 'N/A')}")
        except:
            print("✅ URL отвечает, но не JSON")
    else:
        print(f"⚠️ URL недоступен (статус {response.status_code})")
        
except Exception as e:
    print(f"❌ URL недоступен: {e}")

# Устанавливаем webhook несмотря ни на что
print(f"\n🔧 Принудительно устанавливаем webhook...")

set_url = f'https://api.telegram.org/bot{token}/setWebhook'
webhook_data = {
    'url': webhook_url,
    'allowed_updates': ['message', 'edited_message', 'callback_query'],
    'drop_pending_updates': True,  # Очищаем накопившиеся сообщения
    'secret_token': 'QxLZquGScgx1QmwsuUSfJU6HpyTUJoHf2XD4QisrjCk'  # Из кода webhook.py
}

try:
    response = requests.post(set_url, json=webhook_data, timeout=10)
    data = response.json()
    
    if data.get('ok'):
        print("✅ Webhook успешно установлен!")
        print(f"   URL: {webhook_url}")
        print("   ✅ Очищены накопившиеся сообщения")
        print("   🔑 Secret token установлен")
        
        # Проверяем статус
        print("\n📊 Проверяем статус webhook...")
        info_url = f'https://api.telegram.org/bot{token}/getWebhookInfo'
        info_response = requests.get(info_url, timeout=10)
        info_data = info_response.json()
        
        if info_data.get('ok'):
            webhook_info = info_data.get('result', {})
            print(f"   URL: {webhook_info.get('url', 'N/A')}")
            print(f"   Pending: {webhook_info.get('pending_update_count', 0)}")
            
            if webhook_info.get('last_error_message'):
                print(f"   ⚠️ Последняя ошибка: {webhook_info.get('last_error_message')}")
            else:
                print("   ✅ Ошибок нет")
        
    else:
        print(f"❌ Ошибка установки webhook: {data}")
        
except Exception as e:
    print(f"❌ Ошибка: {e}")

print("\n" + "="*50)
print("💡 СЛЕДУЮЩИЕ ШАГИ:")
print("1. Дождитесь 1-2 минуты")
print("2. Отправьте сообщение боту: /start")
print("3. Проверьте логи Railway на наличие webhook запросов")
print("4. Если не работает - возможно нужен другой Railway URL формат")