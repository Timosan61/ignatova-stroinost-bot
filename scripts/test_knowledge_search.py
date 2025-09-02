#!/usr/bin/env python3
"""
Тест системы поиска в базе знаний через Zep Knowledge Graph
"""

import os
import sys
import asyncio
import logging
from dotenv import load_dotenv

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.agent import ConversationAgent

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_knowledge_search():
    """Тестирует поиск в базе знаний"""
    
    print("🧪 Тестируем систему поиска в базе знаний...")
    
    # Создаём агента
    agent = ConversationAgent()
    
    if not agent.zep_client:
        print("❌ Zep клиент не инициализирован. Проверьте ZEP_API_KEY.")
        return
    
    # Тестовые запросы
    test_queries = [
        "как работать с возражениями клиентов?",
        "какие есть скрипты для старой базы?",
        "что такое диагностика психотипа?",
        "сколько стоит марафон похудения?",
        "как закрывать продажи?",
        "что делать если клиент говорит дорого?",
        "техники активного слушания",
        "триггер потери для холодных клиентов"
    ]
    
    print(f"\n📋 Тестируем {len(test_queries)} запросов:\n")
    
    for i, query in enumerate(test_queries, 1):
        print(f"🔍 Запрос {i}: {query}")
        
        try:
            # Ищем в базе знаний
            context = await agent.search_knowledge_base(query, limit=3)
            
            if context:
                print(f"✅ Найдено {len(context)} символов контекста")
                # Показываем первые 200 символов
                preview = context[:200] + "..." if len(context) > 200 else context
                print(f"📄 Превью: {preview}")
            else:
                print("❌ Ничего не найдено")
                
        except Exception as e:
            print(f"❌ Ошибка поиска: {e}")
            
        print("-" * 60)
    
    # Тестируем полную генерацию ответа
    print("\n🤖 Тестируем полную генерацию ответа с использованием базы знаний:")
    
    test_message = "Клиент говорит что дорого и у него нет денег. Что делать?"
    print(f"Вопрос: {test_message}")
    
    try:
        response = await agent.generate_response(
            user_message=test_message,
            session_id="test_knowledge_session",
            user_name="Тестер"
        )
        
        print(f"✅ Ответ бота: {response}")
        
    except Exception as e:
        print(f"❌ Ошибка генерации ответа: {e}")

if __name__ == "__main__":
    asyncio.run(test_knowledge_search())