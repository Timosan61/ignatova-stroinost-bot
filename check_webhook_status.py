#!/usr/bin/env python3
"""
Проверка статуса webhook через Telegram API
"""
import os
import requests
import json

# Получаем токен из переменной окружения или из файла .env
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
    print("Установите переменную окружения или добавьте в .env файл")
    exit(1)

print(f"🔑 Токен найден: {token[:20]}...")

# Проверяем информацию о webhook
url = f'https://api.telegram.org/bot{token}/getWebhookInfo'

try:
    print(f"🔍 Запрос к: {url}")
    response = requests.get(url, timeout=10)
    data = response.json()
    
    if data.get('ok'):
        webhook_info = data.get('result', {})
        print("\n📍 ИНФОРМАЦИЯ О WEBHOOK:")
        print(f"   URL: {webhook_info.get('url', '❌ Не установлен')}")
        print(f"   Pending updates: {webhook_info.get('pending_update_count', 0)}")
        print(f"   Max connections: {webhook_info.get('max_connections', 40)}")
        print(f"   Allowed updates: {webhook_info.get('allowed_updates', 'Все')}")
        print(f"   Has custom certificate: {webhook_info.get('has_custom_certificate', False)}")
        print(f"   IP address: {webhook_info.get('ip_address', 'N/A')}")
        
        last_error = webhook_info.get('last_error_message')
        if last_error:
            print(f"   ⚠️ Последняя ошибка: {last_error}")
            print(f"   🕐 Время ошибки: {webhook_info.get('last_error_date', 'N/A')}")
        else:
            print("   ✅ Ошибок нет")
            
        # Анализируем проблему
        webhook_url = webhook_info.get('url', '')
        if not webhook_url:
            print("\n❌ ПРОБЛЕМА: Webhook URL не установлен!")
            print("   Решение: Нужно установить webhook URL")
        else:
            print(f"\n✅ Webhook URL установлен: {webhook_url}")
            
            # Проверяем allowed_updates
            allowed = webhook_info.get('allowed_updates', [])
            if allowed:
                has_business = any('business' in update for update in allowed)
                has_message = 'message' in allowed
                
                print(f"\n📋 РАЗРЕШЕННЫЕ СОБЫТИЯ:")
                for update in allowed:
                    print(f"   - {update}")
                    
                if has_business and not has_message:
                    print("\n⚠️ ВОЗМОЖНАЯ ПРОБЛЕМА: Webhook настроен только для Business API")
                    print("   Если у вас нет Business аккаунта, добавьте 'message' в allowed_updates")
                elif has_message:
                    print("\n✅ Обычные сообщения разрешены")
                    
        pending = webhook_info.get('pending_update_count', 0)
        if pending > 0:
            print(f"\n⚠️ ВНИМАНИЕ: {pending} необработанных обновлений в очереди")
            print("   Возможно, webhook не отвечает или отвечает неправильно")
            
    else:
        print(f"❌ Ошибка API: {data}")
        
except Exception as e:
    print(f"❌ Ошибка запроса: {e}")

print("\n" + "="*50)
print("💡 РЕКОМЕНДАЦИИ:")
print("1. Если нет Business аккаунта - включите обычные 'message' события")
print("2. Если есть pending updates - проверьте что webhook отвечает 200 OK") 
print("3. Если есть ошибки - проверьте доступность URL и SSL сертификат")