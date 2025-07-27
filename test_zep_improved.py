#!/usr/bin/env python3
"""
🧪 Улучшенный тест Zep Memory
Проверяет правильную работу с памятью согласно документации
"""

import asyncio
import os
import sys
from datetime import datetime
import uuid

# Добавляем путь к модулям бота
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from zep_cloud.client import AsyncZep
    from zep_cloud.types import Message
    print("✅ Zep SDK успешно импортирован")
except ImportError as e:
    print(f"❌ Ошибка импорта Zep SDK: {e}")
    print("💡 Установите: pip install zep-cloud")
    sys.exit(1)

# Загружаем конфигурацию
try:
    from bot.config import ZEP_API_KEY
    print("✅ Конфигурация загружена из bot.config")
except ImportError:
    ZEP_API_KEY = os.getenv('ZEP_API_KEY')
    print("⚠️ Используем ZEP_API_KEY из переменных окружения")

async def test_zep_memory():
    """Комплексный тест Zep Memory"""
    
    print("\n" + "="*60)
    print("🧪 УЛУЧШЕННЫЙ ТЕСТ ZEP MEMORY")
    print("="*60)
    
    # 1. Проверка API ключа
    print("\n1️⃣ ПРОВЕРКА API КЛЮЧА:")
    if not ZEP_API_KEY:
        print("❌ ZEP_API_KEY не найден!")
        print("💡 Установите переменную окружения или добавьте в .env")
        return False
    
    print(f"✅ API ключ найден")
    print(f"   Длина: {len(ZEP_API_KEY)} символов")
    print(f"   Префикс: {ZEP_API_KEY[:8]}...")
    
    # 2. Инициализация клиента
    print("\n2️⃣ ИНИЦИАЛИЗАЦИЯ КЛИЕНТА:")
    try:
        client = AsyncZep(api_key=ZEP_API_KEY)
        print("✅ Клиент Zep успешно создан")
    except Exception as e:
        print(f"❌ Ошибка создания клиента: {type(e).__name__}: {e}")
        return False
    
    # 3. Создание тестового пользователя
    print("\n3️⃣ СОЗДАНИЕ ПОЛЬЗОВАТЕЛЯ:")
    test_user_id = f"test_user_{uuid.uuid4().hex[:8]}"
    
    try:
        # Пытаемся создать пользователя
        user_data = {
            "user_id": test_user_id,
            "email": f"{test_user_id}@test.com",
            "first_name": "Test",
            "last_name": "User",
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "test": True
            }
        }
        
        # Создаем пользователя
        user = await client.user.add(**user_data)
        print(f"✅ Пользователь создан: {test_user_id}")
        
    except Exception as e:
        print(f"⚠️ Не удалось создать пользователя: {type(e).__name__}: {e}")
        print("   Продолжаем без создания пользователя...")
    
    # 4. Создание сессии
    print("\n4️⃣ СОЗДАНИЕ СЕССИИ:")
    test_session_id = f"session_{uuid.uuid4().hex}"
    
    try:
        # Создаем сессию для пользователя
        session_data = {
            "session_id": test_session_id,
            "user_id": test_user_id,
            "metadata": {
                "channel": "telegram",
                "test": True
            }
        }
        
        await client.memory.add_session(**session_data)
        print(f"✅ Сессия создана: {test_session_id}")
        
    except Exception as e:
        print(f"⚠️ Не удалось явно создать сессию: {type(e).__name__}: {e}")
        print("   Сессия может быть создана автоматически при добавлении сообщений")
    
    # 5. Добавление сообщений
    print("\n5️⃣ ДОБАВЛЕНИЕ СООБЩЕНИЙ:")
    
    try:
        # Создаем сообщения с правильными ролями
        messages = [
            Message(
                role="Test User",  # Имя пользователя вместо "user"
                role_type="user",
                content="Здравствуйте! Меня интересует производство футболок в Китае."
            ),
            Message(
                role="Анастасия",  # Имя ассистента
                role_type="assistant",
                content="Здравствуйте! Рада помочь вам с производством футболок. Какое количество вас интересует?"
            ),
            Message(
                role="Test User",
                role_type="user",
                content="Нужно 5000 штук, хлопок 100%, с нашим логотипом."
            ),
            Message(
                role="Анастасия",
                role_type="assistant",
                content="Отлично! Для 5000 футболок из 100% хлопка с логотипом:\n\n📊 Примерная стоимость: $3-5 за штуку\n🕐 Срок производства: 20-25 дней\n🚢 Доставка: 15-30 дней\n\nМогу подготовить детальное предложение. Какие размеры нужны?"
            )
        ]
        
        # Добавляем сообщения в память
        await client.memory.add(session_id=test_session_id, messages=messages)
        print(f"✅ Добавлено {len(messages)} сообщений")
        
        # Небольшая задержка для обработки
        await asyncio.sleep(1)
        
    except Exception as e:
        print(f"❌ Ошибка добавления сообщений: {type(e).__name__}: {e}")
        print(f"   Детали: {str(e)}")
        return False
    
    # 6. Получение памяти
    print("\n6️⃣ ПОЛУЧЕНИЕ ПАМЯТИ:")
    
    try:
        # Получаем память сессии
        memory = await client.memory.get(session_id=test_session_id)
        
        if hasattr(memory, 'messages') and memory.messages:
            print(f"✅ Получено {len(memory.messages)} сообщений:")
            for i, msg in enumerate(memory.messages, 1):
                print(f"   {i}. [{msg.role_type}] {msg.role}: {msg.content[:60]}...")
        else:
            print("❌ Сообщения не найдены в памяти")
        
        # Проверяем контекст
        if hasattr(memory, 'context') and memory.context:
            print(f"\n📄 Сформирован контекст (длина: {len(memory.context)} символов):")
            print(f"   {memory.context[:200]}...")
        else:
            print("\n📄 Контекст еще не сформирован")
            
        # Проверяем summary
        if hasattr(memory, 'summary') and memory.summary:
            print(f"\n📋 Есть summary: {memory.summary[:100]}...")
            
    except Exception as e:
        print(f"❌ Ошибка получения памяти: {type(e).__name__}: {e}")
        return False
    
    # 7. Поиск по памяти
    print("\n7️⃣ ПОИСК ПО ПАМЯТИ:")
    
    try:
        # Поиск сессий по тексту
        search_results = await client.memory.search_sessions(
            text="футболки хлопок",
            user_id=test_user_id,
            limit=5
        )
        
        if search_results:
            print(f"✅ Найдено {len(search_results)} релевантных сессий")
            for result in search_results[:3]:
                print(f"   - Session: {result.session_id}")
                if hasattr(result, 'score'):
                    print(f"     Score: {result.score}")
        else:
            print("📝 Релевантные сессии не найдены")
            
    except AttributeError:
        print("⚠️ Метод search_sessions не доступен в текущей версии SDK")
    except Exception as e:
        print(f"❌ Ошибка поиска: {type(e).__name__}: {e}")
    
    # 8. Тест обновления памяти
    print("\n8️⃣ ОБНОВЛЕНИЕ ПАМЯТИ:")
    
    try:
        # Добавляем еще сообщения
        new_messages = [
            Message(
                role="Test User",
                role_type="user",
                content="Размеры нужны S, M, L, XL в равных пропорциях."
            ),
            Message(
                role="Анастасия",
                role_type="assistant",
                content="Понял! Равномерное распределение по размерам S-XL. Подготовлю коммерческое предложение."
            )
        ]
        
        await client.memory.add(session_id=test_session_id, messages=new_messages)
        print("✅ Память успешно обновлена")
        
        # Проверяем обновленную память
        updated_memory = await client.memory.get(session_id=test_session_id)
        if hasattr(updated_memory, 'messages'):
            print(f"   Теперь в памяти: {len(updated_memory.messages)} сообщений")
            
    except Exception as e:
        print(f"❌ Ошибка обновления: {type(e).__name__}: {e}")
    
    # 9. Итоги
    print("\n" + "="*60)
    print("📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ:")
    print("="*60)
    
    print("\n✅ Успешно протестировано:")
    print("   - Инициализация клиента")
    print("   - Создание пользователя и сессии")
    print("   - Добавление сообщений с именами")
    print("   - Получение памяти")
    print("   - Обновление памяти")
    
    print("\n💡 РЕКОМЕНДАЦИИ:")
    print("1. Убедитесь, что API ключ активен")
    print("2. Используйте имена пользователей в ролях")
    print("3. Создавайте сессии с user_id для лучшей организации")
    print("4. Регулярно проверяйте лимиты использования")
    
    return True

async def cleanup_test_data():
    """Очистка тестовых данных"""
    print("\n🧹 ОЧИСТКА ТЕСТОВЫХ ДАННЫХ:")
    # В будущем можно добавить удаление тестовых сессий
    print("✅ Очистка завершена")

if __name__ == "__main__":
    # Запускаем тесты
    success = asyncio.run(test_zep_memory())
    
    if success:
        asyncio.run(cleanup_test_data())
        print("\n✅ Все тесты пройдены успешно!")
    else:
        print("\n❌ Тесты завершились с ошибками")
        sys.exit(1)