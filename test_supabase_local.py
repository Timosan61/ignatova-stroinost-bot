#!/usr/bin/env python3
"""
Local Test: Supabase vs Qdrant Search Comparison

Тестирует Supabase vector search локально без Railway deployment.
Сравнивает результаты с текущей производительностью Qdrant.

Usage:
    python3 test_supabase_local.py
"""

import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Добавить корень в PYTHONPATH
root_dir = Path(__file__).parent
sys.path.insert(0, str(root_dir))

# Load environment variables
load_dotenv()

# ВАЖНО: Включить Supabase, отключить Qdrant/Graphiti для чистого теста
os.environ['USE_SUPABASE'] = 'true'
os.environ['USE_QDRANT'] = 'false'
os.environ['GRAPHITI_ENABLED'] = 'false'

from bot.services.supabase_service import get_supabase_service


async def test_supabase_search():
    """Тест Supabase semantic search с тем же запросом что и Qdrant"""

    print("=" * 70)
    print("🧪 LOCAL TEST: Supabase Vector Search")
    print("=" * 70)

    # Получить сервис
    service = get_supabase_service()

    if not service.enabled:
        print("\n❌ Supabase service НЕ включен!")
        print("   Проверь .env:")
        print("     - SUPABASE_URL")
        print("     - SUPABASE_SERVICE_KEY")
        print("     - OPENAI_API_KEY")
        print("     - USE_SUPABASE=true")
        return

    print(f"\n✅ Supabase Service Enabled")
    print(f"   URL: {os.getenv('SUPABASE_URL', 'N/A')}")
    print(f"   Table: {os.getenv('SUPABASE_TABLE', 'course_knowledge')}")
    print(f"   Embedding Model: {os.getenv('OPENAI_EMBEDDING_MODEL', 'text-embedding-3-small')}")

    # 1. Health Check
    print("\n" + "-" * 70)
    print("1️⃣ Health Check:")
    print("-" * 70)

    health = await service.health_check()
    print(f"   Status: {health.get('status', 'unknown')}")
    print(f"   Enabled: {health.get('enabled', False)}")
    print(f"   Total Entities: {health.get('total_entities', 0):,}")

    if health.get('status') != 'healthy':
        print("\n❌ Health check failed! Проверь подключение к Supabase.")
        return

    # 2. Test Query (тот же запрос из Telegram теста)
    test_query = "как мне есть что хочу и не толстеть?"

    print("\n" + "-" * 70)
    print(f"2️⃣ Test Query: '{test_query}'")
    print("-" * 70)

    print("\n⏳ Выполняется semantic search...")

    # СНАЧАЛА пробуем с низким порогом чтобы увидеть ANY результаты
    results = await service.search_semantic(
        query=test_query,
        limit=20,  # Тот же лимит что и в Qdrant тесте
        score_threshold=0.3,  # Снижен порог для отладки (было 0.5)
        entity_type=None  # Искать во всех типах
    )

    # 3. Анализ результатов
    print("\n" + "-" * 70)
    print("3️⃣ Результаты Supabase:")
    print("-" * 70)

    print(f"\n📊 Total Found: {len(results)}")

    if results:
        # Средняя релевантность
        avg_score = sum(r.get('score', 0) for r in results) / len(results)
        print(f"⭐ Avg Relevance: {avg_score:.2f}")

        # Распределение по типам
        entity_types = {}
        for r in results:
            et = r.get('entity_type', 'unknown')
            entity_types[et] = entity_types.get(et, 0) + 1

        entity_types_str = ', '.join(f'{k}:{v}' for k, v in sorted(entity_types.items()))
        print(f"📁 Entity Types: {entity_types_str}")

        # Топ 10 результатов
        print("\n" + "-" * 70)
        print("4️⃣ Top 10 Results:")
        print("-" * 70)

        for i, result in enumerate(results[:10], 1):
            title = result.get('title', 'N/A')
            score = result.get('score', 0)
            entity_type = result.get('entity_type', 'unknown')
            content = result.get('content', '')

            # Обрезать title и content для читаемости
            title_short = (title[:70] + '...') if len(title) > 70 else title
            content_preview = (content[:150] + '...') if len(content) > 150 else content

            print(f"\n   {i}. [{entity_type.upper()}] (score: {score:.3f})")
            print(f"      Title: {title_short}")
            print(f"      Preview: {content_preview}")

        # Лучшие результаты по типам
        print("\n" + "-" * 70)
        print("5️⃣ Лучшие результаты по типам:")
        print("-" * 70)

        for entity_type in ['lesson', 'faq', 'correction', 'question']:
            type_results = [r for r in results if r.get('entity_type') == entity_type]
            if type_results:
                best = type_results[0]
                print(f"\n   📌 {entity_type.upper()}: (score: {best.get('score', 0):.3f})")
                print(f"      {best.get('title', 'N/A')[:80]}")

    else:
        print("\n❌ No results found!")
        print("   Попробуй:")
        print("     - Уменьшить score_threshold")
        print("     - Проверить что данные загружены в Supabase")

    # 4. Сравнение с Qdrant
    print("\n" + "=" * 70)
    print("6️⃣ СРАВНЕНИЕ: Supabase vs Qdrant")
    print("=" * 70)

    print("\n🔵 Qdrant Results (из Telegram теста):")
    print("   📊 Total: 20 найдено")
    print("   ⭐ Avg Relevance: 0.67")
    print("   📁 Entity Types: lesson:1, question:11, correction:8")
    print("   🤖 Response: ❌ FALLBACK (\"обратиться к Наталье напрямую\")")

    print("\n🟣 Supabase Results:")
    if results:
        print(f"   📊 Total: {len(results)} найдено")
        print(f"   ⭐ Avg Relevance: {avg_score:.2f}")
        print(f"   📁 Entity Types: {entity_types_str}")

        # Оценка качества
        if avg_score > 0.67:
            quality = "✅ ЛУЧШЕ чем Qdrant"
        elif avg_score >= 0.60:
            quality = "⚠️ ПОХОЖЕ на Qdrant"
        else:
            quality = "❌ ХУЖЕ чем Qdrant"

        print(f"   📈 Quality: {quality}")

        # Проверка есть ли lessons в топе
        top_5_types = [r.get('entity_type') for r in results[:5]]
        if 'lesson' in top_5_types or 'faq' in top_5_types:
            print("   ✅ Lessons/FAQ в топ-5 результатов (хорошо!)")
        else:
            print("   ⚠️ Lessons/FAQ НЕ в топ-5 (может быть проблема)")

    else:
        print("   ❌ No results (критическая проблема!)")

    # 5. Рекомендации
    print("\n" + "=" * 70)
    print("7️⃣ РЕКОМЕНДАЦИИ:")
    print("=" * 70)

    if not results:
        print("\n❌ Supabase не возвращает результаты:")
        print("   1. Проверь что миграция завершена (должно быть 3,234 entities)")
        print("   2. Проверь embeddings в Supabase Dashboard")
        print("   3. Попробуй уменьшить score_threshold")

    elif avg_score > 0.67 and ('lesson' in top_5_types or 'faq' in top_5_types):
        print("\n✅ Supabase ЛУЧШЕ чем Qdrant!")
        print("   Следующие шаги:")
        print("   1. Установи в Railway:")
        print("      USE_SUPABASE=true")
        print("      USE_QDRANT=false")
        print("      GRAPHITI_ENABLED=false")
        print("   2. Дождись деплоя (~2 минуты)")
        print("   3. Протестируй в Telegram с тем же запросом")

    elif avg_score >= 0.60:
        print("\n⚠️ Supabase ПОХОЖ на Qdrant:")
        print("   Supabase может работать, но не сильно лучше.")
        print("   Рекомендую:")
        print("   - Протестировать ещё 3-5 запросов")
        print("   - Сравнить качество ответов")
        print("   - Решить стоит ли переключаться")

    else:
        print("\n❌ Supabase ХУЖЕ чем Qdrant:")
        print("   Не рекомендую переключаться на Supabase.")
        print("   Возможные причины:")
        print("   - OpenAI embeddings не подходят для этого датасета")
        print("   - Нужна fine-tuning embeddings")
        print("   - Стоит остаться на Qdrant (sentence-transformers)")

    print("\n" + "=" * 70)
    print("✅ TEST COMPLETE")
    print("=" * 70)


async def test_multiple_queries():
    """Дополнительный тест: несколько запросов для полной картины"""

    print("\n\n")
    print("=" * 70)
    print("🧪 ДОПОЛНИТЕЛЬНЫЙ ТЕСТ: Множественные запросы")
    print("=" * 70)

    service = get_supabase_service()

    if not service.enabled:
        print("❌ Supabase service не включен, пропускаю дополнительный тест")
        return

    # Набор тестовых запросов (разные типы вопросов)
    test_queries = [
        "как правильно делать мозгоритм?",
        "что делать если вес встал?",
        "можно ли есть сладкое на курсе?",
        "как справиться со срывом?",
        "как работает техника возврата?",
    ]

    results_summary = []

    for i, query in enumerate(test_queries, 1):
        print(f"\n{i}. Query: '{query}'")

        results = await service.search_semantic(
            query=query,
            limit=10,
            score_threshold=0.3,  # Снижен порог для отладки
            entity_type=None
        )

        if results:
            avg_score = sum(r.get('score', 0) for r in results) / len(results)
            top_type = results[0].get('entity_type', 'unknown')

            print(f"   Results: {len(results)}, Avg Score: {avg_score:.2f}, Top Type: {top_type}")

            results_summary.append({
                'query': query,
                'count': len(results),
                'avg_score': avg_score,
                'top_type': top_type
            })
        else:
            print(f"   ❌ No results")
            results_summary.append({
                'query': query,
                'count': 0,
                'avg_score': 0.0,
                'top_type': 'none'
            })

    # Общая сводка
    print("\n" + "-" * 70)
    print("ОБЩАЯ СВОДКА:")
    print("-" * 70)

    if results_summary:
        total_avg = sum(r['avg_score'] for r in results_summary if r['count'] > 0)
        count_with_results = len([r for r in results_summary if r['count'] > 0])

        if count_with_results > 0:
            overall_avg = total_avg / count_with_results
            print(f"\nСредняя релевантность по всем запросам: {overall_avg:.2f}")
            print(f"Успешных запросов: {count_with_results}/{len(test_queries)}")

            if overall_avg > 0.70:
                print("✅ Отличное качество поиска!")
            elif overall_avg > 0.60:
                print("⚠️ Приемлемое качество поиска")
            else:
                print("❌ Низкое качество поиска")
        else:
            print("❌ Ни один запрос не вернул результаты!")


if __name__ == "__main__":
    print("\n🚀 Запуск локального теста Supabase...\n")

    # Основной тест
    asyncio.run(test_supabase_search())

    # Дополнительный тест (автоматически запускается)
    print("\n\n📋 Запуск дополнительного теста с 5 запросами (занимает ~30 сек)...\n")
    asyncio.run(test_multiple_queries())

    print("\n✅ Все тесты завершены!")
