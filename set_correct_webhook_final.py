#!/usr/bin/env python3
"""
Установка правильного webhook URL
"""
import os
import requests

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

# ПРАВИЛЬНЫЙ URL от пользователя
correct_url = "https://ignatova-stroinost-bot-production.up.railway.app/webhook"

print(f"\n🎯 Устанавливаем ПРАВИЛЬНЫЙ webhook: {correct_url}")

# Сначала проверим что наш бот доступен
base_url = "https://ignatova-stroinost-bot-production.up.railway.app"
print(f"🔍 Проверяем доступность бота: {base_url}")

try:
    response = requests.get(base_url, timeout=10)
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Бот найден: {data.get('bot', 'N/A')}")
        print(f"   Статус: {data.get('status', 'N/A')}")
        print(f"   AI: {data.get('ai_status', 'N/A')}")
    else:
        print(f"⚠️ Неожиданный статус: {response.status_code}")
except Exception as e:
    print(f"❌ Ошибка проверки: {e}")

# Устанавливаем webhook
print(f"\n🔧 Устанавливаем webhook...")
set_url = f'https://api.telegram.org/bot{token}/setWebhook'
webhook_data = {
    'url': correct_url,
    'allowed_updates': ['message', 'edited_message', 'callback_query', 'business_connection', 'business_message'],
    'drop_pending_updates': True,
    'secret_token': 'QxLZquGScgx1QmwsuUSfJU6HpyTUJoHf2XD4QisrjCk'
}

try:
    response = requests.post(set_url, json=webhook_data, timeout=10)
    data = response.json()
    
    if data.get('ok'):
        print("✅ Webhook успешно установлен!")
        print(f"   URL: {correct_url}")
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
print("🎯 ГОТОВО!")
print("Теперь отправьте сообщение боту: /start")
print("Бот должен ответить!")