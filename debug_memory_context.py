#!/usr/bin/env python3
"""
🔍 Отладка контекста памяти бота
Проверяет как бот формирует контекст для LLM
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from bot.agent import TextilProAgent

async def debug_memory_context():
    print("=" * 60)
    print("🔍 ОТЛАДКА КОНТЕКСТА ПАМЯТИ БОТА")
    print("=" * 60)
    
    # Создаем агента
    agent = TextilProAgent()
    
    print(f"\n📊 СТАТУС ИНИЦИАЛИЗАЦИИ:")
    print(f"   Zep клиент: {'✅ Да' if agent.zep_client else '❌ Нет'}")
    print(f"   OpenAI: {'✅ Да' if agent.openai_client else '❌ Нет'}")
    print(f"   Anthropic: {'✅ Да' if agent.anthropic_client else '❌ Нет'}")
    
    if not agent.zep_client:
        print("❌ Zep клиент не инициализирован!")
        return
    
    # Используем тестовую сессию из предыдущего теста
    test_session_id = "conversation_test_12345"
    
    print(f"\n🧠 ТЕСТ ПОЛУЧЕНИЯ КОНТЕКСТА:")
    print(f"   Session ID: {test_session_id}")
    
    # 1. Получаем контекст как в боте
    print("\n1️⃣ ПОЛУЧЕНИЕ ZEP КОНТЕКСТА:")
    try:
        zep_context = await agent.get_zep_memory_context(test_session_id)
        print(f"✅ Контекст получен, длина: {len(zep_context)}")
        if zep_context:
            print(f"📄 Контекст: {zep_context[:300]}...")
        else:
            print("📄 Контекст пуст")
    except Exception as e:
        print(f"❌ Ошибка получения контекста: {e}")
        zep_context = ""
    
    # 2. Получаем последние сообщения
    print("\n2️⃣ ПОЛУЧЕНИЕ ПОСЛЕДНИХ СООБЩЕНИЙ:")
    try:
        zep_history = await agent.get_zep_recent_messages(test_session_id, limit=6)
        print(f"✅ История получена, длина: {len(zep_history)}")
        if zep_history:
            print(f"📝 История:\n{zep_history}")
        else:
            print("📝 История пуста")
    except Exception as e:
        print(f"❌ Ошибка получения истории: {e}")
        zep_history = ""
    
    # 3. Формируем системный промпт как в боте
    print("\n3️⃣ ФОРМИРОВАНИЕ СИСТЕМНОГО ПРОМПТА:")
    
    system_prompt = agent.instruction.get("system_instruction", "")
    print(f"📋 Базовая инструкция: {len(system_prompt)} символов")
    
    # Добавляем контекст и историю как в generate_response
    if zep_context:
        system_prompt += f"\n\nКонтекст предыдущих разговоров:\n{zep_context}"
        print("✅ Контекст добавлен в промпт")
    else:
        print("⚠️ Контекст НЕ добавлен (пуст)")
    
    if zep_history:
        system_prompt += f"\n\nПоследние сообщения:\n{zep_history}"
        print("✅ История добавлена в промпт")
    else:
        print("⚠️ История НЕ добавлена (пуста)")
    
    print(f"\n📏 ИТОГОВЫЙ ПРОМПТ:")
    print(f"   Общая длина: {len(system_prompt)} символов")
    
    # 4. Тестируем генерацию ответа
    print("\n4️⃣ ТЕСТ ГЕНЕРАЦИИ ОТВЕТА:")
    test_question = "О чем мы с тобой говорили вчера? Напомни детали заказа"
    
    try:
        print(f"❓ Вопрос: {test_question}")
        
        # Проверяем, есть ли ключевые слова в промпте
        key_words = ["рубашк", "100", "хлопок", "бел", "логотип", "15000"]
        found_words = []
        for word in key_words:
            if word.lower() in system_prompt.lower():
                found_words.append(word)
        
        print(f"🔍 Найдено ключевых слов в промпте: {len(found_words)}/{len(key_words)}")
        print(f"   Найдены: {found_words}")
        
        if len(found_words) >= 4:
            print("✅ Достаточно контекста для ответа на вопрос о вчерашнем разговоре")
        else:
            print("❌ Недостаточно контекста - бот может не помнить детали")
        
        # Пробуем сгенерировать ответ (только если есть LLM)
        if agent.openai_client or agent.anthropic_client:
            print("\n🤖 Генерируем тестовый ответ...")
            response = await agent.generate_response(test_question, test_session_id, "Анна")
            print(f"📝 Ответ бота: {response[:200]}...")
            
            # Проверяем, упоминает ли бот детали
            response_lower = response.lower()
            mentioned_details = []
            for word in key_words:
                if word.lower() in response_lower:
                    mentioned_details.append(word)
            
            print(f"🎯 Упомянуто деталей в ответе: {len(mentioned_details)}/{len(key_words)}")
            if len(mentioned_details) >= 3:
                print("✅ Бот хорошо помнит детали разговора")
            else:
                print("⚠️ Бот плохо помнит детали разговора")
        else:
            print("⚠️ LLM недоступен для генерации ответа")
            
    except Exception as e:
        print(f"❌ Ошибка генерации ответа: {e}")
    
    print("\n" + "=" * 60)
    print("🔍 ДИАГНОСТИКА ЗАВЕРШЕНА")
    print("=" * 60)

# Запускаем диагностику
if __name__ == "__main__":
    asyncio.run(debug_memory_context())