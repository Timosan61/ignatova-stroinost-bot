"""
Загрузка базы знаний курса в SimpleFalkorDB
Использует существующий парсер из parse_knowledge_base.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, '/home/coder/projects/bot_cloning_railway/clones/ignatova-stroinost-bot')

from bot.services.simple_falkordb_service import get_simple_falkordb_service
from scripts.parse_knowledge_base import KnowledgeBaseParser


async def load_all_knowledge():
    """Загрузить всю базу знаний в SimpleFalkorDB"""

    print("\n" + "="*80)
    print("📚 ЗАГРУЗКА БАЗЫ ЗНАНИЙ В SimpleFalkorDB")
    print("="*80 + "\n")

    # 1. Инициализация сервиса
    print("🔵 Шаг 1: Инициализация SimpleFalkorDB...")
    service = get_simple_falkordb_service()

    if not service.enabled:
        print("❌ SimpleFalkorDB не включен!")
        return

    print("✅ SimpleFalkorDB готов к работе\n")

    # 2. Проверка подключения
    print("🔵 Шаг 2: Проверка подключения...")
    health = await service.health_check()
    print(f"   Status: {health.get('status')}")
    print(f"   Total nodes: {health.get('total_nodes', 0)}\n")

    # 3. Парсинг данных
    print("🔵 Шаг 3: Парсинг базы знаний...")

    kb_dir = Path('/home/coder/projects/bot_cloning_railway/clones/ignatova-stroinost-bot/KNOWLEDGE_BASE')
    parser = KnowledgeBaseParser(kb_dir)

    print("   📖 Парсинг FAQ_EXTENDED.md...")
    faq_entries = parser.parse_faq(kb_dir / 'FAQ_EXTENDED.md')
    print(f"   ✅ FAQ: {len(faq_entries)} записей")

    print("   📖 Парсинг KNOWLEDGE_BASE_FULL.md...")
    lesson_chunks = parser.parse_lessons(kb_dir / 'KNOWLEDGE_BASE_FULL.md', chunk_size=800)
    print(f"   ✅ Уроки: {len(lesson_chunks)} chunks")

    print("   📖 Парсинг curator_corrections_ALL.json...")
    corrections = parser.parse_corrections(kb_dir / 'curator_corrections_ALL.json')
    print(f"   ✅ Корректировки: {len(corrections)} записей\n")

    total_entities = len(faq_entries) + len(lesson_chunks) + len(corrections)
    print(f"📊 Всего entities для загрузки: {total_entities}\n")

    # 4. Загрузка FAQ
    print("🔵 Шаг 4: Загрузка FAQ...")
    faq_success = 0
    faq_failed = 0

    for i, faq in enumerate(faq_entries, 1):
        # Формируем контент
        content = f"Вопрос: {faq.question}\nОтвет: {faq.answer}"

        success, node_id = await service.add_text(
            content=content,
            text_type="faq",
            source="FAQ_EXTENDED",
            metadata={
                "category": faq.category,
                "frequency": faq.frequency,
                "question": faq.question
            }
        )

        if success:
            faq_success += 1
            if i % 5 == 0:
                print(f"   ✅ FAQ: {i}/{len(faq_entries)} загружено")
        else:
            faq_failed += 1
            print(f"   ❌ FAQ #{i} не удалось загрузить")

    print(f"✅ FAQ завершено: {faq_success} успешно, {faq_failed} ошибок\n")

    # 5. Загрузка уроков
    print("🔵 Шаг 5: Загрузка уроков...")
    lessons_success = 0
    lessons_failed = 0

    for i, lesson in enumerate(lesson_chunks, 1):
        # Формируем контент
        content = f"Урок {lesson.lesson_number}, Часть {lesson.chunk_index}: {lesson.title}\n\n{lesson.content}"

        success, node_id = await service.add_text(
            content=content,
            text_type="lesson",
            source="KNOWLEDGE_BASE_FULL",
            metadata={
                "lesson_number": lesson.lesson_number,
                "chunk_index": lesson.chunk_index,
                "title": lesson.title
            }
        )

        if success:
            lessons_success += 1
            if i % 10 == 0:
                print(f"   ✅ Уроки: {i}/{len(lesson_chunks)} загружено")
        else:
            lessons_failed += 1
            print(f"   ❌ Урок #{i} не удалось загрузить")

    print(f"✅ Уроки завершено: {lessons_success} успешно, {lessons_failed} ошибок\n")

    # 6. Загрузка корректировок
    print("🔵 Шаг 6: Загрузка корректировок...")
    corr_success = 0
    corr_failed = 0

    for i, corr in enumerate(corrections, 1):
        # Формируем контент
        content = f"Корректировка ({corr.error_type}):\nИсходный текст: {corr.student_text}\nИсправление: {corr.correction}"
        if corr.explanation:
            content += f"\nОбъяснение: {corr.explanation}"

        success, node_id = await service.add_text(
            content=content,
            text_type="correction",
            source="CURATOR_CORRECTIONS",
            metadata={
                "error_type": corr.error_type,
                "student_text": corr.student_text[:100]  # Первые 100 символов
            }
        )

        if success:
            corr_success += 1
            if i % 20 == 0:
                print(f"   ✅ Корректировки: {i}/{len(corrections)} загружено")
        else:
            corr_failed += 1
            print(f"   ❌ Корректировка #{i} не удалось загрузить")

    print(f"✅ Корректировки завершено: {corr_success} успешно, {corr_failed} ошибок\n")

    # 7. Итоговая статистика
    print("="*80)
    print("📊 ИТОГОВАЯ СТАТИСТИКА")
    print("="*80)

    stats = await service.get_stats()
    print(f"\n✅ Всего загружено в SimpleFalkorDB:")
    print(f"   - FAQ: {faq_success}/{len(faq_entries)}")
    print(f"   - Уроки: {lessons_success}/{len(lesson_chunks)}")
    print(f"   - Корректировки: {corr_success}/{len(corrections)}")
    print(f"   - ИТОГО: {faq_success + lessons_success + corr_success}/{total_entities}")

    print(f"\n📈 Статистика графа:")
    print(f"   - Total nodes: {stats.get('total_nodes', 0)}")
    print(f"   - By type: {stats.get('by_type', {})}")

    if faq_failed + lessons_failed + corr_failed > 0:
        print(f"\n⚠️ Ошибок при загрузке: {faq_failed + lessons_failed + corr_failed}")
    else:
        print(f"\n🎉 Все entities загружены без ошибок!")

    print("\n" + "="*80 + "\n")


async def test_search_queries():
    """Протестировать поиск по загруженным данным"""

    print("\n" + "="*80)
    print("🔍 ТЕСТИРОВАНИЕ ПОИСКА")
    print("="*80 + "\n")

    service = get_simple_falkordb_service()

    test_queries = [
        "мозгоритм",
        "возражения",
        "техника прощения",
        "курс всепрощающая",
        "трансформация"
    ]

    for i, query in enumerate(test_queries, 1):
        print(f"🔍 Запрос {i}: '{query}'")

        results = await service.search_fulltext(query, limit=3)

        print(f"   Найдено: {len(results)} результатов")

        for j, result in enumerate(results, 1):
            content_preview = result['content'][:100] + "..." if len(result['content']) > 100 else result['content']
            print(f"\n   Результат {j}:")
            print(f"   - Type: {result['type']}")
            print(f"   - Source: {result['source']}")
            print(f"   - Relevance: {result['relevance_score']}")
            print(f"   - Content: {content_preview}")

        print()

    print("="*80 + "\n")


async def main():
    """Главная функция"""

    # 1. Загрузка базы знаний
    await load_all_knowledge()

    # 2. Тестирование поиска
    await test_search_queries()

    print("✅ Загрузка и тестирование завершены!")


if __name__ == "__main__":
    asyncio.run(main())
