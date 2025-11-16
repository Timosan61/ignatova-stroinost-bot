#!/usr/bin/env python3
"""
OpenAI Models Diagnostic Script
Проверяет какие модели доступны и фактически используются
"""

import os
import sys
import json
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any

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

import openai
from bot.config import OPENAI_API_KEY, MODEL_NAME, SMALL_MODEL_NAME

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


async def check_api_key() -> bool:
    """Проверить валидность API ключа"""
    print_header("1. Проверка API ключа")

    if not OPENAI_API_KEY:
        print_error("OPENAI_API_KEY не найден в .env")
        return False

    # Скрываем середину ключа
    masked_key = f"{OPENAI_API_KEY[:10]}...{OPENAI_API_KEY[-10:]}"
    print_info(f"API Key: {masked_key}")

    try:
        client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)

        # Простейший запрос для проверки валидности ключа
        models = await client.models.list()

        print_success(f"API ключ валиден! Доступно моделей: {len(models.data)}")
        return True

    except openai.AuthenticationError as e:
        print_error(f"Ошибка аутентификации: {e}")
        return False
    except Exception as e:
        print_error(f"Ошибка при проверке ключа: {type(e).__name__}: {e}")
        return False


async def list_available_models() -> list:
    """Получить список доступных моделей"""
    print_header("2. Доступные модели OpenAI")

    try:
        client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)
        models = await client.models.list()

        # Фильтруем только GPT модели
        gpt_models = [
            model for model in models.data
            if 'gpt' in model.id.lower()
        ]

        print_info(f"Всего GPT моделей: {len(gpt_models)}")
        print("\nСписок GPT моделей:")
        for model in sorted(gpt_models, key=lambda x: x.id):
            print(f"  • {model.id}")

        return gpt_models

    except Exception as e:
        print_error(f"Ошибка при получении списка моделей: {type(e).__name__}: {e}")
        return []


async def test_model_request(model_name: str) -> Optional[Dict[str, Any]]:
    """Тестовый запрос к модели"""
    print_header(f"3. Тестовый запрос к модели: {model_name}")

    try:
        client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)

        print_info(f"Запрашиваемая модель: {model_name}")
        print_info("Отправляем тестовый запрос...")

        response = await client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say 'test' in one word."}
            ],
            max_tokens=10,
            temperature=0.1
        )

        # Получаем фактически использованную модель из ответа
        actual_model = response.model

        print_success(f"Запрос успешен!")
        print_info(f"Запрошенная модель: {model_name}")
        print_info(f"Фактическая модель: {actual_model}")

        # Проверяем совпадение
        if model_name != actual_model:
            print_warning(f"НЕСООТВЕТСТВИЕ! Запрошена '{model_name}', но использована '{actual_model}'")
        else:
            print_success("Модели совпадают ✓")

        print(f"\nОтвет: {response.choices[0].message.content}")
        print(f"Usage: {response.usage.total_tokens} tokens ({response.usage.prompt_tokens} prompt + {response.usage.completion_tokens} completion)")

        return {
            "requested_model": model_name,
            "actual_model": actual_model,
            "matches": model_name == actual_model,
            "response": response.choices[0].message.content,
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }
        }

    except openai.NotFoundError as e:
        print_error(f"Модель '{model_name}' не найдена: {e}")
        return None
    except Exception as e:
        print_error(f"Ошибка при тестовом запросе: {type(e).__name__}: {e}")
        return None


async def check_config() -> None:
    """Проверить текущую конфигурацию"""
    print_header("4. Текущая конфигурация моделей")

    print(f"MODEL_NAME (Graphiti): {Colors.YELLOW}{MODEL_NAME}{Colors.NC}")
    print(f"SMALL_MODEL_NAME (Graphiti): {Colors.YELLOW}{SMALL_MODEL_NAME}{Colors.NC}")

    # Проверяем переменные окружения
    env_model = os.getenv('MODEL_NAME')
    env_small_model = os.getenv('SMALL_MODEL_NAME')

    if env_model:
        print_info(f"Environment MODEL_NAME: {env_model}")
    else:
        print_warning("Environment MODEL_NAME не установлена (используется default)")

    if env_small_model:
        print_info(f"Environment SMALL_MODEL_NAME: {env_small_model}")
    else:
        print_warning("Environment SMALL_MODEL_NAME не установлена (используется default)")


async def main():
    """Главная функция"""
    print(f"\n{Colors.CYAN}🔍 OpenAI Models Diagnostic Script{Colors.NC}\n")

    # 1. Проверка API ключа
    api_valid = await check_api_key()
    if not api_valid:
        print_error("\nДиагностика прервана из-за невалидного API ключа")
        sys.exit(1)

    # 2. Список доступных моделей
    models = await list_available_models()

    # 3. Тестовый запрос к gpt-4o-mini
    test_result = await test_model_request("gpt-4o-mini")

    # 4. Проверка конфигурации
    await check_config()

    # Финальный отчет
    print_header("5. Финальный отчёт")

    if test_result:
        if test_result['matches']:
            print_success("✓ Модель использована корректно")
            print_success(f"✓ Запрошена и использована: {test_result['actual_model']}")
        else:
            print_warning("⚠️  ОБНАРУЖЕНО НЕСООТВЕТСТВИЕ!")
            print_warning(f"   Запрошена: {test_result['requested_model']}")
            print_warning(f"   Использована: {test_result['actual_model']}")
            print_warning("   OpenAI API может автоматически роутить на другие модели")

    print(f"\n{Colors.GREEN}Диагностика завершена{Colors.NC}\n")


if __name__ == '__main__':
    asyncio.run(main())
