#!/usr/bin/env python3
"""
Отладка: проверка содержимого memory сессий и тестирование поиска
"""

import os
import asyncio
import logging
from dotenv import load_dotenv
from zep_cloud.client import AsyncZep

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def debug_memory_sessions():
    """Отладка memory сессий"""
    zep_api_key = os.getenv('ZEP_API_KEY')
    if not zep_api_key:
        print("❌ ZEP_API_KEY не найден!")
        return
    
    zep_client = AsyncZep(api_key=zep_api_key)
    
    # Тестируем несколько сессий
    test_sessions = [
        "knowledge_objections_session_1",
        "knowledge_scripts_session_1",
        "knowledge_sales_methodology_session_1"
    ]
    
    for session_id in test_sessions:
        print(f"\n🔍 Проверяем сессию: {session_id}")
        
        try:
            # Получаем память сессии
            memory = await zep_client.memory.get(session_id=session_id)
            
            if memory:
                print(f"✅ Сессия существует")
                print(f"📝 Количество сообщений: {len(memory.messages) if memory.messages else 0}")
                
                if memory.messages:
                    # Показываем первые несколько сообщений
                    print("📄 Первые сообщения:")
                    for i, msg in enumerate(memory.messages[:4]):
                        role = msg.role_type or msg.role
                        content = msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
                        print(f"  {i+1}. [{role}]: {content}")
                    
                    # Тестируем поиск в этой сессии
                    print(f"\n🔍 Тестируем поиск в сессии {session_id}:")
                    test_queries = [
                        "возражения",
                        "скрипт", 
                        "продажи",
                        "клиент"
                    ]
                    
                    for query in test_queries:
                        try:
                            search_result = await zep_client.memory.search(
                                session_id=session_id,
                                query=query,
                                limit=1
                            )
                            
                            if search_result and hasattr(search_result, 'results') and search_result.results:
                                result_count = len(search_result.results)
                                print(f"  '{query}': ✅ найдено {result_count} результатов")
                                
                                # Показываем первый результат
                                first_result = search_result.results[0]
                                if hasattr(first_result, 'message') and first_result.message:
                                    content = first_result.message.content[:150] + "..."
                                    print(f"    Превью: {content}")
                            else:
                                print(f"  '{query}': ❌ ничего не найдено")
                                
                        except Exception as e:
                            print(f"  '{query}': ❌ ошибка поиска: {e}")
                    
            else:
                print("❌ Сессия не найдена или пуста")
                
        except Exception as e:
            print(f"❌ Ошибка получения сессии: {e}")

if __name__ == "__main__":
    asyncio.run(debug_memory_sessions())