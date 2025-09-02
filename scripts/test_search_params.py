#!/usr/bin/env python3
"""
Тестирование разных параметров для memory.search
"""

import os
import asyncio
from dotenv import load_dotenv
from zep_cloud.client import AsyncZep

load_dotenv()

async def test_search_params():
    zep_api_key = os.getenv('ZEP_API_KEY')
    zep_client = AsyncZep(api_key=zep_api_key)
    
    session_id = "knowledge_objections_session_1"
    
    # Разные варианты параметров
    search_variants = [
        {"text": "возражения", "limit": 3},
        {"message": "возражения", "limit": 3},
        {"content": "возражения", "limit": 3},
        {"search": "возражения", "limit": 3},
        {"q": "возражения", "limit": 3}
    ]
    
    for i, params in enumerate(search_variants):
        try:
            print(f"\n🧪 Тест {i+1}: параметры {params}")
            result = await zep_client.memory.search(
                session_id=session_id,
                **params
            )
            print(f"✅ Успешно! Результат: {type(result)}")
            if hasattr(result, 'results') and result.results:
                print(f"📄 Найдено {len(result.results)} результатов")
        except Exception as e:
            print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    asyncio.run(test_search_params())