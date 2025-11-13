#!/usr/bin/env python3
"""
Тест webhook endpoint - отправляет тестовое сообщение напрямую
"""
import requests
import json

# Тестовый update от Telegram
test_update = {
    "update_id": 999999,
    "message": {
        "message_id": 123,
        "from": {
            "id": 123456789,
            "is_bot": False,
            "first_name": "Test",
            "username": "testuser",
            "language_code": "ru"
        },
        "chat": {
            "id": 123456789,
            "first_name": "Test",
            "username": "testuser",
            "type": "private"
        },
        "date": 1234567890,
        "text": "Привет!"
    }
}

# URL Railway
webhook_url = "https://ignatova-stroinost-bot-production.up.railway.app/webhook"

print("🧪 Отправляем тестовый update на webhook...")
print(f"📡 URL: {webhook_url}")
print(f"📦 Payload: {json.dumps(test_update, indent=2, ensure_ascii=False)}\n")

try:
    response = requests.post(webhook_url, json=test_update, timeout=30)
    print(f"✅ Статус: {response.status_code}")
    print(f"📄 Ответ: {response.text}")

    if response.status_code == 200:
        print("\n✅ Webhook работает!")
    else:
        print(f"\n❌ Webhook вернул ошибку: {response.status_code}")

except Exception as e:
    print(f"❌ Ошибка при отправке: {e}")
