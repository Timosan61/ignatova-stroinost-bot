#!/usr/bin/env python3
"""
Тест бота через webhook simulation
"""
import requests
import json

def simulate_telegram_message():
    """Симулируем сообщение от Telegram"""
    webhook_url = "https://ignatova-stroinost-bot-production.up.railway.app/webhook"
    
    # Симулируем сообщение от пользователя
    update = {
        "update_id": 12345,
        "message": {
            "message_id": 1,
            "date": 1693737600,
            "chat": {
                "id": 123456789,
                "type": "private"
            },
            "from": {
                "id": 123456789,
                "is_bot": False,
                "first_name": "Artem",
                "username": "artemtest"
            },
            "text": "Как обработать возражение 'слишком дорого'?"
        }
    }
    
    try:
        print("📤 Отправляем тестовое сообщение...")
        response = requests.post(webhook_url, json=update, timeout=30)
        
        print(f"📥 Статус ответа: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Ответ сервера: {result}")
        else:
            print(f"❌ Ошибка: {response.text}")
            
    except requests.exceptions.Timeout:
        print("⏱️ Timeout - бот долго обрабатывает запрос")
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    simulate_telegram_message()