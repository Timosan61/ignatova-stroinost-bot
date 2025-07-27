#!/usr/bin/env python3
"""
🧪 Тестирование Zep Memory
Проверяет работоспособность памяти диалогов
"""

import asyncio
import os
from dotenv import load_dotenv
from zep_cloud.client import AsyncZep
from zep_cloud.types import Message

load_dotenv()

ZEP_API_KEY = os.getenv('ZEP_API_KEY')

print("=" * 60)
print("🧪 ТЕСТИРОВАНИЕ ZEP MEMORY")
print("=" * 60)

# 1. Проверка наличия ключа
print("\n1️⃣ ПРОВЕРКА API КЛЮЧА:")
if not ZEP_API_KEY:
    print("❌ ZEP_API_KEY не установлен в переменных окружения!")
    print("💡 Добавьте в .env или Railway: ZEP_API_KEY=ваш_ключ")
    exit(1)
else:
    print(f"✅ ZEP_API_KEY найден (длина: {len(ZEP_API_KEY)} символов)")
    print(f"🔑 Начинается с: {ZEP_API_KEY[:8]}...")

# 2. Тест подключения
async def test_zep():
    print("\n2️⃣ ТЕСТ ПОДКЛЮЧЕНИЯ К ZEP:")
    
    try:
        client = AsyncZep(api_key=ZEP_API_KEY)
        print("✅ Клиент создан успешно")
    except Exception as e:
        print(f"❌ Ошибка создания клиента: {e}")
        return
    
    # 3. Тест сессии
    print("\n3️⃣ ТЕСТ РАБОТЫ С СЕССИЕЙ:")
    test_session_id = "test_session_12345"
    
    try:
        # Добавляем сообщения
        messages = [
            Message(
                role="user",
                role_type="user",
                content="Привет, как дела?"
            ),
            Message(
                role="assistant",
                role_type="assistant", 
                content="Привет! Я бот Textile Pro, помогу с производством одежды."
            )
        ]
        
        await client.memory.add(session_id=test_session_id, messages=messages)
        print(f"✅ Сообщения добавлены в сессию {test_session_id}")
        
    except Exception as e:
        print(f"❌ Ошибка добавления сообщений: {type(e).__name__}: {e}")
        print("💡 Возможные причины:")
        print("   - Неверный API ключ")
        print("   - Проблемы с подключением к Zep Cloud")
        print("   - Превышен лимит запросов")
        return
    
    # 4. Получение памяти
    print("\n4️⃣ ПОЛУЧЕНИЕ ПАМЯТИ:")
    
    try:
        # Получаем память сессии
        memory = await client.memory.get(session_id=test_session_id)
        print(f"✅ Память получена для сессии {test_session_id}")
        
        if memory.messages:
            print(f"📝 Найдено сообщений: {len(memory.messages)}")
            for i, msg in enumerate(memory.messages[:3]):
                print(f"   {i+1}. {msg.role}: {msg.content[:50]}...")
        else:
            print("📝 Сообщений не найдено")
            
        if memory.context:
            print(f"📄 Контекст: {memory.context[:100]}...")
        else:
            print("📄 Контекст пуст")
            
    except Exception as e:
        print(f"❌ Ошибка получения памяти: {type(e).__name__}: {e}")
    
    # 5. Поиск в памяти
    print("\n5️⃣ ПОИСК В ПАМЯТИ:")
    
    try:
        # Поиск по тексту
        search_results = await client.memory.search_sessions(
            text="производство",
            limit=5
        )
        
        if search_results:
            print(f"✅ Найдено сессий: {len(search_results)}")
            for result in search_results:
                print(f"   - Session: {result.session_id}, Score: {result.score}")
        else:
            print("📝 Сессий не найдено")
            
    except Exception as e:
        print(f"❌ Ошибка поиска: {type(e).__name__}: {e}")
    
    print("\n" + "=" * 60)
    print("✅ Тестирование завершено!")
    print("=" * 60)

# Запускаем тест
if __name__ == "__main__":
    asyncio.run(test_zep())
    
    print("\n💡 РЕКОМЕНДАЦИИ:")
    print("1. Если тесты прошли успешно - Zep работает корректно")
    print("2. Если есть ошибки - проверьте API ключ в Railway")
    print("3. Убедитесь, что ключ активен на https://app.getzep.com")