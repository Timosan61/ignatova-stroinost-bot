#!/usr/bin/env python3
"""
Поиск рабочего Railway URL для нашего бота
"""
import requests
import time

# Возможные варианты Railway URL на основе внутреннего URL: ignatova-stroinost-bot.railway.internal
possible_urls = [
    # Различные форматы Railway
    "https://ignatova-stroinost-bot.up.railway.app",
    "https://ignatova-stroinost-bot-production.up.railway.app", 
    "https://ignatova-stroinost-bot.railway.app",
    "https://web-production-{number}.up.railway.app",  # Найдем нужный номер
    "https://production-{number}.up.railway.app"
]

# Проверим диапазон номеров для web-production-XXXX
production_numbers = ['f742', '1234', '5678', '9abc', 'def0', '472c', '8d3f', '2a5b']

print("🔍 Поиск рабочего Railway URL...")
print("=====================================")

working_urls = []

# Проверяем основные URL
base_urls = [
    "https://ignatova-stroinost-bot.up.railway.app",
    "https://ignatova-stroinost-bot-production.up.railway.app",
    "https://ignatova-stroinost-bot.railway.app"
]

for url in base_urls:
    try:
        print(f"   Проверяем: {url}")
        response = requests.get(url, timeout=5)
        print(f"   Статус: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"   Ответ: {data}")
                if 'status' in data or 'bot' in data:
                    print(f"   ✅ РАБОЧИЙ URL НАЙДЕН!")
                    working_urls.append(url)
                else:
                    print(f"   ⚠️ Отвечает, но это не наш бот")
            except:
                content = response.text[:200]
                print(f"   Содержимое: {content}...")
                if "bot" in content.lower() or "ignatova" in content.lower():
                    print(f"   ✅ Возможно наш бот (не JSON)")
                    working_urls.append(url)
    except Exception as e:
        print(f"   ❌ Недоступен: {e}")
    
    print()

# Проверяем варианты с номерами
print("🔍 Проверяем варианты с номерами...")
print("=====================================")

for num in production_numbers:
    url = f"https://web-production-{num}.up.railway.app"
    try:
        print(f"   Проверяем: {url}")
        response = requests.get(url, timeout=5)
        print(f"   Статус: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"   Ответ: {data}")
                if 'status' in data or 'bot' in data:
                    print(f"   ✅ РАБОЧИЙ URL НАЙДЕН!")
                    working_urls.append(url)
                    break
            except:
                content = response.text[:200]
                print(f"   Содержимое: {content}...")
                if "bot" in content.lower() or "ignatova" in content.lower():
                    print(f"   ✅ Возможно наш бот")
                    working_urls.append(url)
                    break
                else:
                    print(f"   ⚠️ Другой сервис")
    except Exception as e:
        print(f"   ❌ Недоступен: {e}")

print("\n" + "="*50)
print("📋 РЕЗУЛЬТАТЫ:")
if working_urls:
    print(f"✅ Найдено {len(working_urls)} рабочих URL:")
    for i, url in enumerate(working_urls, 1):
        print(f"   {i}. {url}")
        print(f"      → Webhook: {url}/webhook")
    
    print(f"\n💡 Рекомендуемый URL для webhook:")
    print(f"   {working_urls[0]}/webhook")
else:
    print("❌ НЕ НАЙДЕНО рабочих URL!")
    print("   Возможные причины:")
    print("   1. Сервис не запущен на Railway")
    print("   2. Другой формат URL")
    print("   3. Требуется время для активации")
    
    print("\n💡 Попробуйте:")
    print("   1. Проверить статус деплоя на Railway")
    print("   2. Проверить логи Railway")
    print("   3. Попробовать позже")