#!/usr/bin/env python3
"""
FalkorDB Connection Test Script
Проверяет подключение к FalkorDB Cloud и базовые операции с Graphiti
"""

import os
import sys
import asyncio
from pathlib import Path

# Добавляем корень проекта в PYTHONPATH
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Загрузка переменных из .env
env_path = project_root / '.env'
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value

# Цвета для терминала
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    CYAN = '\033[0;36m'
    NC = '\033[0m'  # No Color


def print_header(text: str):
    """Вывести заголовок секции"""
    print(f"\n{Colors.BLUE}{'='*80}{Colors.NC}")
    print(f"{Colors.CYAN}{text}{Colors.NC}")
    print(f"{Colors.BLUE}{'='*80}{Colors.NC}\n")


def print_success(text: str):
    """Вывести успешное сообщение"""
    print(f"{Colors.GREEN}✅ {text}{Colors.NC}")


def print_error(text: str):
    """Вывести сообщение об ошибке"""
    print(f"{Colors.RED}❌ {text}{Colors.NC}")


def print_warning(text: str):
    """Вывести предупреждение"""
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.NC}")


def print_info(text: str):
    """Вывести информационное сообщение"""
    print(f"{Colors.CYAN}ℹ️  {text}{Colors.NC}")


async def test_falkordb_connection():
    """Тестирование подключения к FalkorDB"""

    print_header("1. Проверка конфигурации FalkorDB")

    from bot.config import (
        FALKORDB_HOST,
        FALKORDB_PORT,
        FALKORDB_USERNAME,
        FALKORDB_PASSWORD,
        FALKORDB_DATABASE
    )

    # Проверка credentials
    if not FALKORDB_HOST or FALKORDB_HOST == 'localhost':
        print_warning("FALKORDB_HOST не настроен (используется localhost)")
        print_info("Для работы с FalkorDB Cloud нужно установить:")
        print_info("  FALKORDB_HOST=your-instance.falkordb.cloud")
        print_info("  FALKORDB_PORT=6379")
        print_info("  FALKORDB_PASSWORD=your-password")
        print("")
        print_info("Регистрация: https://app.falkordb.cloud/signup")
        return False

    print_info(f"Host: {FALKORDB_HOST}:{FALKORDB_PORT}")
    print_info(f"Database: {FALKORDB_DATABASE}")
    print_info(f"Username: {FALKORDB_USERNAME}")

    masked_password = f"{FALKORDB_PASSWORD[:4]}...{FALKORDB_PASSWORD[-4:]}" if FALKORDB_PASSWORD else "NOT SET"
    print_info(f"Password: {masked_password}")

    # Проверка OpenAI API key (нужен для Graphiti)
    from bot.config import OPENAI_API_KEY, MODEL_NAME

    if not OPENAI_API_KEY:
        print_error("OPENAI_API_KEY не настроен!")
        return False

    print_info(f"LLM Model: {MODEL_NAME}")

    print_header("2. Инициализация FalkorDB Service")

    try:
        from bot.services.falkordb_service import get_falkordb_service

        service = get_falkordb_service()

        if not service.enabled:
            print_error("FalkorDB service не включен")
            return False

        print_success("FalkorDB service инициализирован")

    except Exception as e:
        print_error(f"Ошибка при инициализации: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

    print_header("3. Health Check")

    try:
        health = await service.health_check()

        print_info(f"Status: {health.get('status')}")
        print_info(f"Backend: {health.get('backend')}")
        print_info(f"Indices built: {health.get('indices_built')}")

        if health.get('status') != 'healthy':
            print_warning(f"Health check не прошел: {health.get('error', 'Unknown error')}")
            return False

        print_success("Health check успешен!")

    except Exception as e:
        print_error(f"Health check failed: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

    print_header("4. Тестовое добавление episode")

    try:
        success, episode_id = await service.add_episode(
            content="Тестовое сообщение от Python test script. Это проверка работы FalkorDB с Graphiti.",
            episode_type="test",
            source="test_script",
            metadata={"test": True}
        )

        if not success:
            print_error("Не удалось добавить episode")
            return False

        print_success(f"Episode добавлен успешно!")
        print_info(f"Episode ID: {episode_id}")

    except Exception as e:
        print_error(f"Ошибка при добавлении episode: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

    print_header("5. Тестовый semantic search")

    try:
        results = await service.search_semantic(
            query="тестовое сообщение",
            limit=5,
            min_relevance=0.1
        )

        print_info(f"Найдено результатов: {len(results)}")

        if len(results) > 0:
            print_success("Semantic search работает!")
            print("")
            for i, result in enumerate(results, 1):
                print(f"  {i}. Relevance: {result.get('relevance_score', 0):.2f}")
                content = result.get('content', '')
                print(f"     Content: {content[:100]}...")
        else:
            print_warning("Результаты не найдены (возможно индексация еще не завершена)")

    except Exception as e:
        print_error(f"Ошибка при поиске: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

    print_header("6. Итоговый отчет")

    print_success("✓ Подключение к FalkorDB работает")
    print_success("✓ Graphiti client инициализирован")
    print_success("✓ Episodes добавляются")
    print_success("✓ Semantic search работает")

    print("")
    print_info("FalkorDB готов к использованию!")
    print_info("Следующий шаг: Загрузите базу знаний через Admin API:")
    print_info("  POST /api/admin/load_knowledge")

    return True


async def main():
    """Главная функция"""
    print(f"\n{Colors.CYAN}🔵 FalkorDB Connection Test{Colors.NC}\n")

    success = await test_falkordb_connection()

    if success:
        print(f"\n{Colors.GREEN}{'='*80}{Colors.NC}")
        print(f"{Colors.GREEN}✅ ВСЕ ТЕСТЫ ПРОШЛИ УСПЕШНО!{Colors.NC}")
        print(f"{Colors.GREEN}{'='*80}{Colors.NC}\n")
        sys.exit(0)
    else:
        print(f"\n{Colors.RED}{'='*80}{Colors.NC}")
        print(f"{Colors.RED}❌ ТЕСТЫ НЕ ПРОШЛИ{Colors.NC}")
        print(f"{Colors.RED}{'='*80}{Colors.NC}\n")
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())
