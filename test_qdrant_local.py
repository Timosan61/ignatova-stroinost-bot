#!/usr/bin/env python3
"""
Локальный тест Qdrant миграции

Использование:
    python3 test_qdrant_local.py

Этот скрипт позволяет протестировать миграцию локально без deployment.
"""

import os
import sys
import json
from pathlib import Path

# Добавить корень в PYTHONPATH
root_dir = Path(__file__).parent
sys.path.insert(0, str(root_dir))

from dotenv import load_dotenv
load_dotenv()

from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

# Конфигурация
QDRANT_URL = os.getenv('QDRANT_URL')
QDRANT_API_KEY = os.getenv('QDRANT_API_KEY')
QDRANT_COLLECTION = os.getenv('QDRANT_COLLECTION', 'course_knowledge')
EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'all-MiniLM-L6-v2')


def test_connection():
    """Тест подключения к Qdrant"""
    print("🔵 Тест подключения к Qdrant Cloud...")
    print(f"   URL: {QDRANT_URL}")
    print(f"   Collection: {QDRANT_COLLECTION}")
    print("")

    try:
        client = QdrantClient(
            url=QDRANT_URL,
            api_key=QDRANT_API_KEY,
            timeout=30
        )

        # Проверить существование collection
        collections = client.get_collections()
        collection_names = [c.name for c in collections.collections]

        if QDRANT_COLLECTION in collection_names:
            print(f"✅ Collection '{QDRANT_COLLECTION}' найдена")

            # Получить статистику
            collection_info = client.get_collection(QDRANT_COLLECTION)
            print(f"   Points count: {collection_info.points_count}")
            print(f"   Vector size: {collection_info.config.params.vectors.size}")
            print(f"   Distance: {collection_info.config.params.vectors.distance}")
            print(f"   Status: {collection_info.status}")
        else:
            print(f"❌ Collection '{QDRANT_COLLECTION}' НЕ найдена")
            print(f"   Доступные collections: {collection_names}")

        return True

    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
        return False


def test_search():
    """Тест semantic search"""
    print("\n🔍 Тест semantic search...")

    try:
        client = QdrantClient(
            url=QDRANT_URL,
            api_key=QDRANT_API_KEY,
            timeout=30
        )

        # Загрузить encoder
        print(f"   Загрузка модели: {EMBEDDING_MODEL}")
        encoder = SentenceTransformer(EMBEDDING_MODEL)

        # Тестовый запрос
        query = "как простить обиду"
        print(f"   Запрос: '{query}'")

        # Генерировать embedding
        query_vector = encoder.encode(query).tolist()

        # Поиск
        search_result = client.search(
            collection_name=QDRANT_COLLECTION,
            query_vector=query_vector,
            limit=3
        )

        print(f"   Найдено результатов: {len(search_result)}")
        print("")

        for i, hit in enumerate(search_result, 1):
            print(f"   Результат {i}:")
            print(f"     Score: {hit.score:.4f}")
            print(f"     Entity type: {hit.payload.get('entity_type')}")
            print(f"     Title: {hit.payload.get('title')[:80]}...")
            print("")

        return True

    except Exception as e:
        print(f"❌ Ошибка поиска: {e}")
        return False


def test_upload_single():
    """Тест загрузки одного entity"""
    print("\n📤 Тест загрузки entity...")

    try:
        from qdrant_client.models import PointStruct

        client = QdrantClient(
            url=QDRANT_URL,
            api_key=QDRANT_API_KEY,
            timeout=30
        )

        encoder = SentenceTransformer(EMBEDDING_MODEL)

        # Тестовый entity
        test_entity = {
            "id": 999999,  # Integer ID для теста
            "entity_type": "test",
            "title": "Test Entity",
            "content": "This is a test entity for local testing",
            "metadata": {"test": True}
        }

        # Генерировать embedding
        vector = encoder.encode(test_entity["content"]).tolist()

        # Создать point
        point = PointStruct(
            id=test_entity["id"],
            vector=vector,
            payload={
                "entity_type": test_entity["entity_type"],
                "title": test_entity["title"],
                "content": test_entity["content"],
                "metadata": test_entity["metadata"]
            }
        )

        # Upload
        client.upsert(
            collection_name=QDRANT_COLLECTION,
            points=[point]
        )

        print(f"✅ Test entity загружен (ID: {test_entity['id']})")

        # Проверить что появился
        collection_info = client.get_collection(QDRANT_COLLECTION)
        print(f"   Новый points count: {collection_info.points_count}")

        return True

    except Exception as e:
        print(f"❌ Ошибка загрузки: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main entry point"""
    print("=" * 60)
    print("🧪 Локальный тест Qdrant интеграции")
    print("=" * 60)
    print("")

    if not QDRANT_URL or not QDRANT_API_KEY:
        print("❌ QDRANT_URL или QDRANT_API_KEY не настроены в .env")
        sys.exit(1)

    # Тесты
    results = []

    results.append(("Connection", test_connection()))
    results.append(("Search", test_search()))
    results.append(("Upload", test_upload_single()))

    # Итоги
    print("\n" + "=" * 60)
    print("📊 Результаты тестирования:")
    print("=" * 60)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {name:15s} {status}")

    passed = sum(1 for _, r in results if r)
    total = len(results)
    print("")
    print(f"Пройдено: {passed}/{total}")

    if passed == total:
        print("\n✅ Все тесты пройдены! Qdrant готов к использованию.")
    else:
        print("\n⚠️ Некоторые тесты провалились. Проверьте конфигурацию.")


if __name__ == "__main__":
    main()
