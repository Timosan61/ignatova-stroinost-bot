#!/usr/bin/env python3
"""
🧠 Тест памяти разговора с временными ссылками
Проверяет работу памяти в контексте диалога "что мы обсуждали вчера"
"""

import asyncio
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from zep_cloud.client import AsyncZep
from zep_cloud.types import Message

load_dotenv()

ZEP_API_KEY = os.getenv('ZEP_API_KEY')

async def test_conversation_memory():
    print("=" * 60)
    print("🧠 ТЕСТ ПАМЯТИ РАЗГОВОРА С ВРЕМЕННЫМИ ССЫЛКАМИ")
    print("=" * 60)
    
    client = AsyncZep(api_key=ZEP_API_KEY)
    test_session_id = "conversation_test_12345"
    
    # 1. Создаем "вчерашний" разговор
    print("\n1️⃣ СИМУЛЯЦИЯ ВЧЕРАШНЕГО РАЗГОВОРА:")
    yesterday_messages = [
        Message(
            role="Анна",
            role_type="user",
            content="Привет! Хочу заказать пошив 100 рубашек для сотрудников"
        ),
        Message(
            role="Анастасия",
            role_type="assistant",
            content="Здравствуйте, Анна! Отлично, помогу с заказом рубашек. Какую ткань предпочитаете - хлопок или смесовую?"
        ),
        Message(
            role="Анна",
            role_type="user",
            content="Хлопок 100%, белые рубашки с логотипом компании"
        ),
        Message(
            role="Анастасия",
            role_type="assistant",
            content="Понятно! Хлопок 100%, белые, с логотипом. Размерная сетка нужна стандартная? И когда планируете получить заказ?"
        ),
        Message(
            role="Анна",
            role_type="user",
            content="Да, стандартные размеры S-XXL. Нужно к концу месяца"
        ),
        Message(
            role="Анастасия",
            role_type="assistant",
            content="Отлично! Заказ на 100 рубашек хлопок 100%, белые, с логотипом, размеры S-XXL, срок - конец месяца. Стоимость будет 15000 рублей. Подходит?"
        )
    ]
    
    try:
        await client.memory.add(session_id=test_session_id, messages=yesterday_messages)
        print(f"✅ Добавлен 'вчерашний' разговор ({len(yesterday_messages)} сообщений)")
    except Exception as e:
        print(f"❌ Ошибка добавления сообщений: {e}")
        return
    
    # 2. Проверяем память
    print("\n2️⃣ ПРОВЕРКА СОХРАНЕННОЙ ПАМЯТИ:")
    try:
        memory = await client.memory.get(session_id=test_session_id)
        print(f"✅ Получена память сессии {test_session_id}")
        print(f"📝 Сообщений в памяти: {len(memory.messages) if memory.messages else 0}")
        
        if memory.context:
            print(f"📄 Автоконтекст Zep: {memory.context[:200]}...")
        
        # Показываем последние сообщения
        if memory.messages:
            print("\n📋 ПОСЛЕДНИЕ СООБЩЕНИЯ:")
            for i, msg in enumerate(memory.messages[-4:]):
                print(f"   {i+1}. {msg.role}: {msg.content[:70]}...")
                
    except Exception as e:
        print(f"❌ Ошибка получения памяти: {e}")
        return
    
    # 3. Симулируем сегодняшний вопрос
    print("\n3️⃣ СИМУЛЯЦИЯ СЕГОДНЯШНЕГО ВОПРОСА:")
    
    today_messages = [
        Message(
            role="Анна",
            role_type="user",
            content="Привет! О чем мы с тобой говорили вчера? Напомни детали заказа"
        )
    ]
    
    try:
        await client.memory.add(session_id=test_session_id, messages=today_messages)
        print("✅ Добавлен вопрос 'о чем говорили вчера'")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return
    
    # 4. Получаем полную память для ответа
    print("\n4️⃣ АНАЛИЗ ПАМЯТИ ДЛЯ ОТВЕТА:")
    try:
        memory = await client.memory.get(session_id=test_session_id)
        
        print(f"📊 Общее количество сообщений: {len(memory.messages) if memory.messages else 0}")
        
        # Формируем контекст как делает бот
        context_parts = []
        
        if memory.context:
            context_parts.append(f"Контекст Zep: {memory.context}")
        
        if memory.messages:
            recent_messages = memory.messages[-6:]  # Последние 6 как в боте
            history = []
            for msg in recent_messages:
                role = "Пользователь" if msg.role_type == "user" else "Ассистент"
                history.append(f"{role}: {msg.content}")
            context_parts.append("Последние сообщения:\n" + "\n".join(history))
        
        full_context = "\n\n".join(context_parts)
        
        print("\n📝 КОНТЕКСТ ДЛЯ LLM:")
        print("-" * 40)
        print(full_context[:500] + "..." if len(full_context) > 500 else full_context)
        print("-" * 40)
        
        # Проверяем, есть ли ключевые детали заказа
        key_details = {
            "рубашки": "рубашк" in full_context.lower(),
            "100 штук": "100" in full_context,
            "хлопок": "хлопок" in full_context.lower(),
            "белые": "бел" in full_context.lower(),
            "логотип": "логотип" in full_context.lower(),
            "15000 рублей": "15000" in full_context,
            "конец месяца": "месяц" in full_context.lower()
        }
        
        print("\n🔍 АНАЛИЗ КЛЮЧЕВЫХ ДЕТАЛЕЙ:")
        for detail, found in key_details.items():
            status = "✅" if found else "❌"
            print(f"   {status} {detail}: {'найдено' if found else 'не найдено'}")
        
        found_count = sum(key_details.values())
        total_count = len(key_details)
        print(f"\n📈 Найдено деталей: {found_count}/{total_count} ({found_count/total_count*100:.1f}%)")
        
    except Exception as e:
        print(f"❌ Ошибка анализа: {e}")
    
    print("\n" + "=" * 60)
    print("🧠 ЗАКЛЮЧЕНИЕ:")
    if found_count >= total_count * 0.7:  # Если найдено 70%+ деталей
        print("✅ Память работает ОТЛИЧНО - все детали сохранены")
        print("💡 Бот должен корректно отвечать на вопросы о вчерашнем разговоре")
    elif found_count >= total_count * 0.5:
        print("⚠️ Память работает ЧАСТИЧНО - некоторые детали потеряны")
        print("💡 Возможно, нужно улучшить формирование контекста")
    else:
        print("❌ Память работает ПЛОХО - много деталей потеряно")
        print("💡 Проблема в логике сохранения или получения памяти")
    print("=" * 60)

# Запускаем тест
if __name__ == "__main__":
    asyncio.run(test_conversation_memory())