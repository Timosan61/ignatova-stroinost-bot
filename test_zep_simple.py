#!/usr/bin/env python3
"""
Простой тест Zep Memory без внешних зависимостей
"""

import os
import json
import time

# Проверяем наличие API ключа
ZEP_API_KEY = os.getenv('ZEP_API_KEY')

print("=== ПРОСТОЙ ТЕСТ ZEP MEMORY ===")
print(f"\n1. ZEP_API_KEY установлен: {'✅ ДА' if ZEP_API_KEY else '❌ НЕТ'}")

if ZEP_API_KEY:
    print(f"   Длина ключа: {len(ZEP_API_KEY)} символов")
    print(f"   Начинается с: {ZEP_API_KEY[:8]}...")
    
    # Проверяем что ключ выглядит корректно
    if len(ZEP_API_KEY) > 50 and ZEP_API_KEY.startswith('z_'):
        print("   ✅ Ключ выглядит корректно (начинается с 'z_' и достаточной длины)")
    else:
        print("   ⚠️ Ключ может быть некорректным")

print("\n2. Проверка конфигурации бота:")
try:
    from bot.config import ZEP_API_KEY as CONFIG_KEY
    print(f"   ✅ ZEP_API_KEY загружен из bot.config")
    print(f"   Совпадает с .env: {'✅ ДА' if CONFIG_KEY == ZEP_API_KEY else '❌ НЕТ'}")
except ImportError:
    print("   ❌ Не удалось импортировать bot.config")

print("\n3. Проверка инициализации в agent.py:")
try:
    from bot.agent import agent
    print(f"   ✅ Agent загружен")
    print(f"   Zep клиент инициализирован: {'✅ ДА' if agent.zep_client else '❌ НЕТ'}")
    print(f"   Количество локальных сессий: {len(agent.user_sessions)}")
except Exception as e:
    print(f"   ❌ Ошибка загрузки agent: {e}")

print("\n4. Рекомендации:")
if not ZEP_API_KEY:
    print("   1. Добавьте ZEP_API_KEY в файл .env")
    print("   2. Получите ключ на https://app.getzep.com")
    print("   3. Формат: ZEP_API_KEY=z_ваш_ключ_здесь")
elif not (ZEP_API_KEY.startswith('z_') and len(ZEP_API_KEY) > 50):
    print("   1. Проверьте правильность API ключа")
    print("   2. Ключ должен начинаться с 'z_'")
    print("   3. Убедитесь, что скопировали весь ключ")
else:
    print("   ✅ Конфигурация выглядит корректной!")
    print("   Если есть проблемы с подключением:")
    print("   1. Проверьте интернет-соединение")
    print("   2. Убедитесь, что ключ активен на getzep.com")
    print("   3. Проверьте логи бота при запуске")

print("\n" + "="*40)