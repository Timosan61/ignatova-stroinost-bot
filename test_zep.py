#!/usr/bin/env python3
import asyncio
import os
from dotenv import load_dotenv
from zep_cloud.client import AsyncZep
from zep_cloud.types import Message

# Загружаем переменные окружения
load_dotenv()

async def test_zep_connection():
    """Тестирует подключение к Zep Memory"""
    zep_api_key = os.getenv('ZEP_API_KEY')
    
    print("=== Тест Zep Memory ===")
    print(f"🔑 ZEP_API_KEY загружен: {'✅' if zep_api_key else '❌'}")
    
    if not zep_api_key:
        print("❌ ZEP_API_KEY не найден в .env файле!")
        return
    
    print(f"🔑 Длина ключа: {len(zep_api_key)} символов")
    print(f"🔑 Начало ключа: {zep_api_key[:8]}...")
    
    try:
        # Инициализация клиента
        print("\n📡 Подключение к Zep Cloud...")
        zep_client = AsyncZep(api_key=zep_api_key)
        print("✅ Клиент успешно инициализирован!")
        
        # Тестовая сессия
        test_session_id = "test_session_123"
        
        # Добавляем тестовые сообщения
        print(f"\n📝 Добавление сообщений в сессию {test_session_id}...")
        messages = [
            Message(
                role="user",
                role_type="user", 
                content="Привет! Это тестовое сообщение."
            ),
            Message(
                role="assistant",
                role_type="assistant",
                content="Здравствуйте! Я получил ваше тестовое сообщение."
            )
        ]
        
        await zep_client.memory.add(session_id=test_session_id, messages=messages)
        print("✅ Сообщения успешно добавлены!")
        
        # Получаем память
        print(f"\n🔍 Получение памяти для сессии {test_session_id}...")
        memory = await zep_client.memory.get(session_id=test_session_id)
        
        if memory.messages:
            print(f"✅ Найдено {len(memory.messages)} сообщений:")
            for i, msg in enumerate(memory.messages):
                print(f"   {i+1}. {msg.role}: {msg.content}")
        else:
            print("📭 Сообщения не найдены")
            
        if memory.context:
            print(f"\n📄 Контекст: {memory.context}")
        else:
            print("\n📄 Контекст пока не сформирован")
            
        print("\n✅ Тест успешно завершен! Zep Memory работает корректно.")
        
    except Exception as e:
        print(f"\n❌ Ошибка при работе с Zep: {type(e).__name__}")
        print(f"   Детали: {str(e)}")
        print("\n💡 Возможные причины:")
        print("   - Неверный API ключ")
        print("   - Проблемы с подключением к серверу Zep")
        print("   - Истек срок действия API ключа")

if __name__ == "__main__":
    asyncio.run(test_zep_connection())