"""
Тест SimpleFalkorDB сервиса
"""

import asyncio
import sys
sys.path.insert(0, '/home/coder/projects/bot_cloning_railway/clones/ignatova-stroinost-bot')

from bot.services.simple_falkordb_service import get_simple_falkordb_service
from bot.config import FALKORDB_HOST, FALKORDB_PORT, FALKORDB_DATABASE, FALKORDB_USERNAME


async def main():
    print("\n🔵 SimpleFalkorDB Connection Test\n")

    # 1. Проверка конфигурации
    print("="*80)
    print("1. Проверка конфигурации FalkorDB")
    print("="*80)
    print(f"ℹ️  Host: {FALKORDB_HOST}:{FALKORDB_PORT}")
    print(f"ℹ️  Database: {FALKORDB_DATABASE}")
    print(f"ℹ️  Username: {FALKORDB_USERNAME}")
    print()

    # 2. Инициализация service
    print("="*80)
    print("2. Инициализация SimpleFalkorDB Service")
    print("="*80)

    service = get_simple_falkordb_service()

    if service.enabled:
        print("✅ SimpleFalkorDB service инициализирован")
    else:
        print("❌ SimpleFalkorDB service НЕ включен")
        print("\n" + "="*80)
        print("❌ ТЕСТЫ НЕ ПРОШЛИ")
        print("="*80)
        return

    print()

    # 3. Health check
    print("="*80)
    print("3. Health Check")
    print("="*80)

    health = await service.health_check()
    print(f"ℹ️  Status: {health.get('status')}")
    print(f"ℹ️  Backend: {health.get('backend')}")
    print(f"ℹ️  Total nodes: {health.get('total_nodes', 0)}")

    if health.get('status') == 'healthy':
        print("✅ Health check успешен!")
    else:
        print(f"❌ Health check не прошёл: {health.get('error')}")

    print()

    # 4. Тестовое добавление текста
    print("="*80)
    print("4. Тестовое добавление текста")
    print("="*80)

    test_content = "Тестовый текст для SimpleFalkorDB. Это проверка работы графовой базы данных."
    success, node_id = await service.add_text(
        content=test_content,
        text_type="test",
        source="test_script"
    )

    if success:
        print(f"✅ Текст добавлен успешно!")
        print(f"   Node ID: {node_id}")
    else:
        print("❌ Не удалось добавить текст")

    print()

    # 5. Тестовый поиск
    print("="*80)
    print("5. Тестовый поиск")
    print("="*80)

    search_query = "тестовый"
    results = await service.search_fulltext(search_query, limit=5)

    if results:
        print(f"✅ Найдено результатов: {len(results)}")
        for i, result in enumerate(results, 1):
            print(f"\n   Результат {i}:")
            print(f"   - ID: {result.get('id')}")
            print(f"   - Type: {result.get('type')}")
            print(f"   - Content: {result.get('content')[:100]}...")
            print(f"   - Relevance: {result.get('relevance_score')}")
    else:
        print("❌ Результатов не найдено")

    print()

    # 6. Статистика
    print("="*80)
    print("6. Статистика графа")
    print("="*80)

    stats = await service.get_stats()
    print(f"ℹ️  Total nodes: {stats.get('total_nodes', 0)}")
    print(f"ℹ️  By type: {stats.get('by_type', {})}")

    print()

    # Итоговый результат
    print("="*80)
    if service.enabled and success and results:
        print("✅ ВСЕ ТЕСТЫ ПРОШЛИ УСПЕШНО!")
    else:
        print("⚠️ НЕКОТОРЫЕ ТЕСТЫ НЕ ПРОШЛИ")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())
