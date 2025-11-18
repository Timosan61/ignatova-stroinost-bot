#!/usr/bin/env python3
"""
Тест Qdrant unified search с новыми данными
Проверяет что вопросы студентов теперь находятся
"""

import os
import sys
import asyncio
from pathlib import Path

# Добавить корень в PYTHONPATH
root_dir = Path(__file__).parent
sys.path.insert(0, str(root_dir))

# Установить environment variables
os.environ['QDRANT_URL'] = 'https://33d94c1b-cc7f-4b71-82cc-dcee289122f0.eu-central-1-0.aws.cloud.qdrant.io:6333'
os.environ['QDRANT_API_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.UTJlYE3KsxYq-NCTexIE035VcMuZ5KiTAf79ezuMYgg'
os.environ['QDRANT_COLLECTION'] = 'course_knowledge'
os.environ['EMBEDDING_MODEL'] = 'sentence-transformers/all-MiniLM-L6-v2'
os.environ['USE_QDRANT'] = 'true'

from bot.services.qdrant_service import QdrantService


async def test_unified_search():
    """Тест unified search по вопросам студентов"""

    print("=" * 60)
    print("🔍 ТЕСТ QDRANT UNIFIED SEARCH")
    print("=" * 60)
    print()

    # Инициализация Qdrant service
    print("📡 Инициализация Qdrant service...")
    qdrant = QdrantService()

    if not qdrant.enabled:
        print("❌ Qdrant service not enabled!")
        return

    print(f"✅ Qdrant service enabled: {qdrant.collection_name}")
    print()

    # Получить статистику
    print("📊 Статистика Qdrant Collection:")
    stats = await qdrant.get_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    print()

    # Тестовые запросы
    test_queries = [
        {
            "query": "возврат средств за курс",
            "expected_types": ["question", "faq"],
            "description": "Критический запрос - должен найти вопросы студентов"
        },
        {
            "query": "техника прощения обиды",
            "expected_types": ["lesson", "correction", "brainwrite"],
            "description": "Техники курса"
        },
        {
            "query": "как работать с претензиями",
            "expected_types": ["question", "lesson"],
            "description": "Практические вопросы"
        }
    ]

    for idx, test in enumerate(test_queries, 1):
        print(f"🔍 ТЕСТ {idx}/{len(test_queries)}: {test['description']}")
        print(f"   Запрос: \"{test['query']}\"")
        print(f"   Ожидается: {', '.join(test['expected_types'])}")
        print()

        # Unified search (без фильтров по entity_type)
        results = await qdrant.search_semantic(
            query=test['query'],
            limit=10,
            score_threshold=0.3,
            entity_type=None  # БЕЗ ФИЛЬТРОВ - unified search!
        )

        if not results:
            print("   ❌ НЕТ РЕЗУЛЬТАТОВ!")
            print()
            continue

        print(f"   ✅ Найдено: {len(results)} результатов")
        print()

        # Статистика по типам
        entity_types = {}
        for r in results:
            entity_type = r.get('entity_type', 'unknown')
            entity_types[entity_type] = entity_types.get(entity_type, 0) + 1

        print("   📁 Разбивка по типам:")
        for entity_type, count in entity_types.items():
            emoji = "✅" if entity_type in test['expected_types'] else "⚠️"
            print(f"      {emoji} {entity_type}: {count}")
        print()

        # Топ-3 результата
        print("   🏆 Топ-3 результата:")
        for i, result in enumerate(results[:3], 1):
            score = result.get('score', 0)
            entity_type = result.get('entity_type', 'unknown')
            title = result.get('title', '')[:80]

            print(f"      {i}. [{entity_type}] score={score:.3f}")
            print(f"         {title}...")
        print()

        # Проверка что нашлись ожидаемые типы
        found_types = set(entity_types.keys())
        expected_types = set(test['expected_types'])

        if found_types & expected_types:
            print(f"   ✅ УСПЕХ: Найдены ожидаемые типы: {found_types & expected_types}")
        else:
            print(f"   ⚠️ ПРЕДУПРЕЖДЕНИЕ: Не найдены ожидаемые типы")
            print(f"      Ожидалось: {expected_types}")
            print(f"      Найдено: {found_types}")

        print()
        print("-" * 60)
        print()

    print("=" * 60)
    print("✅ ТЕСТЫ ЗАВЕРШЕНЫ")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_unified_search())
