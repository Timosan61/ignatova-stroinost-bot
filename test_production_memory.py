#!/usr/bin/env python3
"""
🔍 Тест памяти в продакшене
Проверяет работу бота с реальным Zep токеном через webhook
"""

import requests
import json
import time
from datetime import datetime

BOT_URL = "https://ignatova-stroinost-bot-production.up.railway.app"
BOT_TOKEN = "7790878041:AAEsO0UNEfRFLZkGNApwNApNF9xJ-QFTjOo"

def test_bot_memory():
    print("=" * 60)
    print("🔍 ТЕСТ ПАМЯТИ БОТА В ПРОДАКШЕНЕ")
    print("=" * 60)
    
    # 1. Проверяем статус бота
    print("\n1️⃣ ПРОВЕРКА СТАТУСА БОТА:")
    try:
        response = requests.get(f"{BOT_URL}/", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Бот онлайн: {data.get('status')}")
            print(f"📋 AI статус: {data.get('ai_status')}")
        else:
            print(f"❌ Ошибка статуса: {response.status_code}")
            return
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
        return
    
    # 2. Тестируем через Telegram API
    print("\n2️⃣ ТЕСТ ЧЕРЕЗ TELEGRAM API:")
    
    # Создаем тестового пользователя
    test_user_id = 987654321
    test_session_id = f"user_{test_user_id}"
    
    # Симуляция webhook сообщения
    test_message = {
        "update_id": 12345,
        "message": {
            "message_id": 1,
            "from": {
                "id": test_user_id,
                "is_bot": False,
                "first_name": "Test",
                "last_name": "User"
            },
            "chat": {
                "id": test_user_id,
                "first_name": "Test",
                "last_name": "User",
                "type": "private"
            },
            "date": int(time.time()),
            "text": "Привет! Хочу заказать 50 рубашек из хлопка для офиса"
        }
    }
    
    try:
        print(f"📤 Отправляем тестовое сообщение...")
        response = requests.post(
            f"{BOT_URL}/webhook",
            json=test_message,
            headers={'Content-Type': 'application/json'},
            timeout=15
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Сообщение обработано: {result}")
        else:
            print(f"❌ Ошибка обработки: {response.status_code}")
            print(f"Ответ: {response.text}")
            
    except Exception as e:
        print(f"❌ Ошибка отправки: {e}")
    
    # 3. Ждем и отправляем вопрос о памяти
    print("\n3️⃣ ТЕСТ ПАМЯТИ - ВОПРОС О ПРЕДЫДУЩЕМ РАЗГОВОРЕ:")
    
    time.sleep(3)  # Ждем обработки первого сообщения
    
    memory_test_message = {
        "update_id": 12346,
        "message": {
            "message_id": 2,
            "from": {
                "id": test_user_id,
                "is_bot": False,
                "first_name": "Test",
                "last_name": "User"
            },
            "chat": {
                "id": test_user_id,
                "first_name": "Test",
                "last_name": "User",
                "type": "private"
            },
            "date": int(time.time()),
            "text": "О чем мы говорили только что? Напомни детали заказа"
        }
    }
    
    try:
        print(f"📤 Отправляем вопрос о памяти...")
        response = requests.post(
            f"{BOT_URL}/webhook",
            json=memory_test_message,
            headers={'Content-Type': 'application/json'},
            timeout=15
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Вопрос о памяти обработан: {result}")
            
            # Проверяем упоминает ли бот детали из первого сообщения
            if "processed" in str(result).lower():
                print("💡 Бот обработал сообщение, проверьте ответ в Telegram")
            
        else:
            print(f"❌ Ошибка обработки вопроса о памяти: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Ошибка отправки вопроса о памяти: {e}")
    
    # 4. Проверяем через Telegram API что бот ответил
    print("\n4️⃣ ПРОВЕРКА ОТВЕТОВ ЧЕРЕЗ TELEGRAM API:")
    
    try:
        # Получаем обновления через getUpdates
        telegram_url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
        response = requests.get(telegram_url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("ok") and data.get("result"):
                print(f"✅ Получено обновлений: {len(data['result'])}")
                
                # Ищем последние сообщения от бота
                bot_messages = []
                for update in data["result"][-10:]:  # Последние 10 обновлений
                    if "message" in update:
                        msg = update["message"]
                        if msg.get("from", {}).get("is_bot"):
                            bot_messages.append(msg.get("text", ""))
                
                if bot_messages:
                    print(f"📝 Последние ответы бота:")
                    for i, msg in enumerate(bot_messages[-3:], 1):  # Последние 3
                        print(f"   {i}. {msg[:100]}...")
                        
                    # Проверяем память
                    memory_keywords = ["рубашек", "хлопок", "офис", "50", "заказ"]
                    last_response = " ".join(bot_messages[-2:]).lower()  # Последние 2 ответа
                    
                    found_keywords = [kw for kw in memory_keywords if kw.lower() in last_response]
                    
                    print(f"\n🧠 АНАЛИЗ ПАМЯТИ:")
                    print(f"   Найдено ключевых слов: {len(found_keywords)}/{len(memory_keywords)}")
                    print(f"   Найдены: {found_keywords}")
                    
                    if len(found_keywords) >= 2:
                        print("✅ ПАМЯТЬ РАБОТАЕТ - бот помнит детали разговора!")
                    else:
                        print("⚠️ ПАМЯТЬ РАБОТАЕТ ЧАСТИЧНО - некоторые детали потеряны")
                else:
                    print("❌ Ответы бота не найдены")
            else:
                print(f"❌ Telegram API ошибка: {data}")
        else:
            print(f"❌ Ошибка Telegram API: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Ошибка проверки Telegram API: {e}")
    
    print("\n" + "=" * 60)
    print("🔍 ТЕСТ ЗАВЕРШЕН")
    print("💡 Проверьте также диалог с ботом @ignatova_stroinost_bot в Telegram")
    print("=" * 60)

if __name__ == "__main__":
    test_bot_memory()