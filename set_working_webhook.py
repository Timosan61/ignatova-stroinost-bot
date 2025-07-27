#!/usr/bin/env python3
"""
Установка webhook с первым рабочим Railway URL
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

# Попробуем установить webhook с рабочим Railway URL
working_url = "https://ignatova-stroinost-bot.railway.app/webhook"

print(f"\n🔧 Устанавливаем webhook: {working_url}")
print("⚠️ ВНИМАНИЕ: Этот URL показывает Railway API страницу, но попробуем")

# Устанавливаем webhook
set_url = f'https://api.telegram.org/bot{token}/setWebhook'
webhook_data = {
    'url': working_url,
    'allowed_updates': ['message', 'edited_message', 'callback_query'],
    'drop_pending_updates': True,  # Очищаем накопившиеся сообщения
    'secret_token': 'QxLZquGScgx1QmwsuUSfJU6HpyTUJoHf2XD4QisrjCk'  # Из кода
}

try:
    response = requests.post(set_url, json=webhook_data, timeout=10)
    data = response.json()
    
    if data.get('ok'):
        print("✅ Webhook установлен!")
        print(f"   URL: {working_url}")
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
print("💡 ДИАГНОСТИКА:")
print("1. Webhook установлен, но URL показывает Railway API")
print("2. Это означает что наш сервис не доступен на этом URL")
print("3. Возможно проблема в Railway конфигурации")
print("4. Нужно проверить:")
print("   - Логи Railway деплоя")
print("   - railway.json конфигурацию")  
print("   - Переменные окружения")
print("   - Статус сервиса")

print("\n🔧 СЛЕДУЮЩИЕ ШАГИ:")
print("1. Попробуйте отправить сообщение боту")
print("2. Если нет ответа - проблема в Railway")
print("3. Возможно нужен ручной редеплой")
print("4. Или исправление конфигурации Railway")