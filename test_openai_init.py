#!/usr/bin/env python3
"""
Тест инициализации OpenAI клиента
"""
import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

print("🔍 Проверка OpenAI API ключа...")
print(f"OPENAI_API_KEY установлен: {'✅ Да' if OPENAI_API_KEY else '❌ Нет'}")

if OPENAI_API_KEY:
    print(f"Длина ключа: {len(OPENAI_API_KEY)} символов")
    print(f"Начинается с: {OPENAI_API_KEY[:10]}...")
    print(f"Заканчивается на: ...{OPENAI_API_KEY[-10:]}")

    # Проверим что это правильный формат
    if OPENAI_API_KEY.startswith('sk-proj-') or OPENAI_API_KEY.startswith('sk-'):
        print("✅ Формат ключа правильный")
    else:
        print(f"⚠️ Необычный формат ключа (начинается с: {OPENAI_API_KEY[:10]})")

    # Попробуем инициализировать клиент
    print("\n🔄 Пытаемся инициализировать OpenAI клиент...")
    try:
        import openai
        client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)
        print("✅ OpenAI клиент инициализирован успешно!")
        print(f"Клиент: {type(client)}")

        # Попробуем простой запрос
        print("\n🧪 Тестируем простой запрос к API...")
        import asyncio

        async def test_request():
            try:
                response = await client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": "Say 'test'"}],
                    max_tokens=10
                )
                return response.choices[0].message.content
            except Exception as e:
                return f"Ошибка: {e}"

        result = asyncio.run(test_request())
        print(f"Результат: {result}")

    except Exception as e:
        print(f"❌ Ошибка инициализации: {e}")
        import traceback
        traceback.print_exc()
else:
    print("❌ OPENAI_API_KEY не установлен!")
