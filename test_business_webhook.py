#!/usr/bin/env python3
"""
Тестовый скрипт для проверки Business API через webhook
Эмулирует business_message с и без business_connection_id
"""

import requests
import json
import os
from datetime import datetime

# Настройки
WEBHOOK_URL = "http://localhost:8000/webhook"  # Для локального теста
# WEBHOOK_URL = "https://bot-production-472c.up.railway.app/webhook"  # Для продакшена

WEBHOOK_SECRET_TOKEN = os.getenv("WEBHOOK_SECRET_TOKEN", "textil_pro_secret_2025")

def send_business_message(text, business_connection_id=None, include_connection_id=True):
    """Отправляет тестовое business_message на webhook"""
    
    # Создаем структуру business_message согласно Telegram API
    update_data = {
        "update_id": 12345678,
        "business_message": {
            "message_id": 1001,
            "date": int(datetime.now().timestamp()),
            "chat": {
                "id": -100123456789,  # Отрицательный ID для бизнес-чата
                "type": "private"
            },
            "from": {
                "id": 987654321,
                "is_bot": False,
                "first_name": "Тестовый Клиент",
                "username": "test_client"
            },
            "text": text
        }
    }
    
    # Добавляем business_connection_id если нужно
    if include_connection_id and business_connection_id:
        update_data["business_message"]["business_connection_id"] = business_connection_id
    
    # Заголовки с secret token
    headers = {
        "Content-Type": "application/json",
        "X-Telegram-Bot-Api-Secret-Token": WEBHOOK_SECRET_TOKEN
    }
    
    print(f"📤 Отправка business_message:")
    print(f"   Текст: {text}")
    print(f"   Connection ID: {business_connection_id if include_connection_id else 'НЕ ВКЛЮЧЕН'}")
    print(f"   URL: {WEBHOOK_URL}")
    
    try:
        response = requests.post(WEBHOOK_URL, json=update_data, headers=headers)
        print(f"   Статус: {response.status_code}")
        print(f"   Ответ: {response.json()}")
        return response.json()
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
        return None

def test_business_connection():
    """Тестирует установку business connection"""
    
    update_data = {
        "update_id": 12345677,
        "business_connection": {
            "id": "biz_conn_test_123",
            "user": {
                "id": 111222333,
                "is_bot": False,
                "first_name": "Бизнес Пользователь"
            },
            "user_chat_id": 111222333,
            "date": int(datetime.now().timestamp()),
            "is_enabled": True
        }
    }
    
    headers = {
        "Content-Type": "application/json",
        "X-Telegram-Bot-Api-Secret-Token": WEBHOOK_SECRET_TOKEN
    }
    
    print(f"🔌 Тестирование business_connection...")
    try:
        response = requests.post(WEBHOOK_URL, json=update_data, headers=headers)
        print(f"   Статус: {response.status_code}")
        print(f"   Ответ: {response.json()}")
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")

if __name__ == "__main__":
    print("🧪 ТЕСТИРОВАНИЕ BUSINESS API WEBHOOK")
    print("="*50)
    
    # Тест 1: Business connection
    print("\n1️⃣ Тест Business Connection:")
    test_business_connection()
    
    # Тест 2: Business message С connection_id
    print("\n2️⃣ Тест Business Message с connection_id:")
    send_business_message(
        text="Привет! Это тестовое сообщение через Business API",
        business_connection_id="biz_conn_test_123",
        include_connection_id=True
    )
    
    # Тест 3: Business message БЕЗ connection_id (для проверки fallback)
    print("\n3️⃣ Тест Business Message БЕЗ connection_id:")
    send_business_message(
        text="Тест без connection_id - должен сработать fallback",
        business_connection_id=None,
        include_connection_id=False
    )
    
    # Тест 4: Проверка обработки ошибок
    print("\n4️⃣ Тест обработки ошибок (очень длинное сообщение):")
    long_text = "Ошибка " * 1000  # Создаем очень длинное сообщение
    send_business_message(
        text=long_text[:4096],  # Telegram ограничение
        business_connection_id="biz_conn_test_123",
        include_connection_id=True
    )
    
    print("\n✅ Тестирование завершено!")
    print("Проверьте логи webhook сервера для деталей.")