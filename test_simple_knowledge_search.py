"""
Тест интеграции SimpleFalkorDB с KnowledgeSearchService
"""

import asyncio
import sys
sys.path.insert(0, '/home/coder/projects/bot_cloning_railway/clones/ignatova-stroinost-bot')

from bot.services.knowledge_search import get_knowledge_search_service


async def test_knowledge_search():
    """Тест поиска через KnowledgeSearchService"""

    print("\n" + "="*80)
    print("🔍 ТЕСТ ИНТЕГРАЦИИ SimpleFalkorDB С KNOWLEDGE SEARCH")
    print("="*80 + "\n")

    # Инициализация
    service = get_knowledge_search_service()

    print("📊 Статус системы:")
    print(f"   - use_qdrant: {service.use_qdrant}")
    print(f"   - use_simple_falkordb: {service.use_simple_falkordb}")
    print(f"   - graphiti_enabled: {service.graphiti_enabled}")
    print()

    # Тестовые запросы
    test_queries = [
        ("мозгоритм", "Техника работы с возражениями"),
        ("вес встал", "Остановка веса"),
        ("6 шагов прощения", "Методология курса"),
        ("трансформация", "Изменения в процессе курса"),
        ("техника прощения", "Конкретная техника")
    ]

    for i, (query, expected) in enumerate(test_queries, 1):
        print(f"{'='*80}")
        print(f"📝 ЗАПРОС {i}: '{query}'")
        print(f"🎯 Ожидается: {expected}")
        print(f"{'='*80}\n")

        # Выполняем поиск
        results = await service.search(query, limit=3)

        print(f"✅ Найдено результатов: {len(results)}\n")

        for j, result in enumerate(results, 1):
            print(f"   📄 Результат {j}:")
            print(f"   - Relevance: {result.relevance_score:.2f}")
            print(f"   - Source: {result.source}")

            # Обрезаем контент для краткости
            content_preview = result.content[:150] + "..." if len(result.content) > 150 else result.content
            print(f"   - Content: {content_preview}")
            print()

        if not results:
            print(f"   ⚠️ Нет результатов для запроса '{query}'\n")

        print()

    print("="*80)
    print("✅ ТЕСТ ЗАВЕРШЁН")
    print("="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(test_knowledge_search())
