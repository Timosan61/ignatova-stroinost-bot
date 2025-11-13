#!/usr/bin/env python3
"""
Тестовый скрипт для проверки подключения к Neo4j и Graphiti

Usage:
    python scripts/test_neo4j_connection.py
"""

import os
import sys
import asyncio
from pathlib import Path

# Добавить корневую директорию в PYTHONPATH
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from dotenv import load_dotenv
load_dotenv()

# Импорт после добавления в path
from bot.services.graphiti_service import GraphitiService, GRAPHITI_AVAILABLE
from bot.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, GRAPHITI_ENABLED


def print_separator(title: str = ""):
    """Красивый разделитель"""
    if title:
        print(f"\n{'=' * 60}")
        print(f"  {title}")
        print(f"{'=' * 60}")
    else:
        print(f"{'=' * 60}")


async def main():
    """Основная функция тестирования"""

    print_separator("Neo4j & Graphiti Connection Test")

    # 1. Проверка environment variables
    print("\n1️⃣  Проверка environment variables:")
    print(f"   NEO4J_URI: {'✅ установлен' if NEO4J_URI else '❌ не установлен'}")
    print(f"   NEO4J_USER: {'✅ установлен' if NEO4J_USER else '❌ не установлен'}")
    print(f"   NEO4J_PASSWORD: {'✅ установлен' if NEO4J_PASSWORD else '❌ не установлен'}")
    print(f"   GRAPHITI_ENABLED: {GRAPHITI_ENABLED}")

    if NEO4J_URI:
        print(f"\n   Neo4j URI: {NEO4J_URI}")

    # 2. Проверка dependencies
    print("\n2️⃣  Проверка dependencies:")
    print(f"   graphiti-core: {'✅ установлен' if GRAPHITI_AVAILABLE else '❌ не установлен'}")

    try:
        import neo4j
        print(f"   neo4j: ✅ установлен (версия {neo4j.__version__})")
    except ImportError:
        print(f"   neo4j: ❌ не установлен")
        print("\n❌ Установите dependencies: pip install graphiti-core neo4j")
        return

    # 3. Проверка настройки
    if not NEO4J_URI or not NEO4J_PASSWORD:
        print("\n❌ Neo4j credentials не настроены!")
        print("\nДобавьте в .env файл:")
        print("   NEO4J_URI=neo4j+s://xxxxx.databases.neo4j.io")
        print("   NEO4J_USER=neo4j")
        print("   NEO4J_PASSWORD=your_password")
        print("   GRAPHITI_ENABLED=true")
        return

    # 4. Инициализация Graphiti Service
    print("\n3️⃣  Инициализация Graphiti Service:")
    service = GraphitiService()

    if not service.enabled:
        print("   ❌ Graphiti service не активирован")
        print("      Проверьте GRAPHITI_ENABLED и credentials")
        return

    print("   ✅ Graphiti service инициализирован")

    # 5. Health check
    print("\n4️⃣  Health check Neo4j подключения:")
    try:
        health = await service.health_check()

        if health.get("status") == "healthy":
            print("   ✅ Neo4j подключение успешно!")
            print(f"      Neo4j URI: {health.get('neo4j_uri')}")

            # Статистика графа
            print("\n5️⃣  Статистика knowledge graph:")
            print(f"      Total nodes: {health.get('total_nodes', 0)}")
            print(f"      Total relationships: {health.get('total_relationships', 0)}")
            print(f"      Total episodes: {health.get('total_episodes', 0)}")

        else:
            print(f"   ❌ Health check failed: {health.get('error')}")

    except Exception as e:
        print(f"   ❌ Ошибка подключения: {e}")

    # 6. Тест добавления episode
    print("\n6️⃣  Тест добавления test episode:")
    try:
        success, result = await service.add_episode(
            content="Это тестовое сообщение для проверки Graphiti.",
            episode_type="test",
            metadata={"source": "connection_test", "test": True},
            source_description="Connection test episode"
        )

        if success:
            print(f"   ✅ Test episode добавлен!")
            print(f"      Episode ID: {result}")
        else:
            print(f"   ❌ Не удалось добавить episode: {result}")

    except Exception as e:
        print(f"   ❌ Ошибка добавления episode: {e}")

    # 7. Тест semantic search
    print("\n7️⃣  Тест semantic search:")
    try:
        results = await service.search_semantic(
            query="тестовое сообщение",
            limit=3
        )

        print(f"   Найдено результатов: {len(results)}")

        if results:
            print("\n   Результаты:")
            for i, r in enumerate(results, 1):
                print(f"      {i}. Similarity: {r.get('similarity', 0):.2f}")
                print(f"         Content: {r.get('content', '')[:80]}...")

    except Exception as e:
        print(f"   ❌ Ошибка поиска: {e}")

    # Закрыть подключение
    service.close()

    print_separator("Test Completed")
    print("\n✅ Все тесты завершены!")
    print("\nСледующие шаги:")
    print("   1. Добавить Neo4j в Railway (если ещё не добавлено)")
    print("   2. Настроить NEO4J_URI, NEO4J_PASSWORD в Railway variables")
    print("   3. Установить GRAPHITI_ENABLED=true в Railway")
    print("   4. Запустить загрузку базы знаний: python scripts/load_knowledge_to_graphiti.py")
    print()


if __name__ == "__main__":
    asyncio.run(main())
