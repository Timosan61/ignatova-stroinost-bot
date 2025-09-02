#!/usr/bin/env python3
"""
Debug: Проверка переменных окружения на Railway
"""
import os

print("🔍 Проверка переменных окружения:")
print(f"TELEGRAM_BOT_TOKEN: {'✅ Установлен' if os.getenv('TELEGRAM_BOT_TOKEN') else '❌ Отсутствует'}")
print(f"OPENAI_API_KEY: {'✅ Установлен' if os.getenv('OPENAI_API_KEY') else '❌ Отсутствует'}")
print(f"ANTHROPIC_API_KEY: {'✅ Установлен' if os.getenv('ANTHROPIC_API_KEY') else '❌ Отсутствует'}")
print(f"ZEP_API_KEY: {'✅ Установлен' if os.getenv('ZEP_API_KEY') else '❌ Отсутствует'}")
print(f"WEBHOOK_SECRET_TOKEN: {'✅ Установлен' if os.getenv('WEBHOOK_SECRET_TOKEN') else '❌ Отсутствует'}")

# Проверим что конфиг загружается
try:
    from bot.config import INSTRUCTION_FILE, OPENAI_API_KEY, ANTHROPIC_API_KEY, ZEP_API_KEY
    print(f"INSTRUCTION_FILE: {INSTRUCTION_FILE}")
    print(f"OpenAI доступен: {bool(OPENAI_API_KEY)}")
    print(f"Anthropic доступен: {bool(ANTHROPIC_API_KEY)}")
    print(f"Zep доступен: {bool(ZEP_API_KEY)}")
except Exception as e:
    print(f"❌ Ошибка config: {e}")

# Проверим что файл инструкций существует
try:
    import json
    with open('data/instruction.json', 'r', encoding='utf-8') as f:
        instruction = json.load(f)
    print(f"✅ instruction.json найден, размер: {len(instruction.get('system_instruction', ''))}")
except Exception as e:
    print(f"❌ Ошибка instruction.json: {e}")