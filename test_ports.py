#!/usr/bin/env python3
"""
Проверка различных портов и эндпоинтов
"""
import requests

# Основные кандидаты URL
base_urls = [
    "https://ignatova-stroinost-bot.railway.app",
    "https://ignatova-stroinost-bot-production.railway.app"
]

# Возможные порты (хотя Railway обычно работает через 443)
ports = ["", ":8000", ":3000", ":5000", ":80"]

# Возможные эндпоинты
endpoints = [
    "/",
    "/webhook", 
    "/health",
    "/status",
    "/api",
    "/bot"
]

print("🔍 ТЕСТИРУЕМ ПОРТЫ И ЭНДПОИНТЫ")
print("=" * 50)

found_bot = False

for base_url in base_urls:
    print(f"\n🌐 Тестируем: {base_url}")
    print("-" * 40)
    
    for port in ports:
        test_url = base_url + port
        
        for endpoint in endpoints:
            full_url = test_url + endpoint
            
            try:
                print(f"   Проверяем: {full_url}")
                response = requests.get(full_url, timeout=5)
                
                print(f"   Статус: {response.status_code}")
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        print(f"   📋 JSON: {str(data)[:100]}...")
                        
                        # Ищем признаки нашего бота
                        if any(key in str(data).lower() for key in ['ignatova', 'textile', 'stroinost', 'bot', 'status']):
                            print(f"   🎉 НАЙДЕН БОТ! {full_url}")
                            found_bot = True
                            
                    except:
                        content = response.text[:200]
                        print(f"   📄 Текст: {content[:100]}...")
                        
                        # Проверяем HTML/текст контент
                        if any(keyword in content.lower() for keyword in ['ignatova', 'textile', 'webhook']):
                            print(f"   🎉 ВОЗМОЖНО БОТ: {full_url}")
                            found_bot = True
                            
                elif response.status_code != 404:
                    print(f"   ⚠️ Неожиданный статус: {response.status_code}")
                    
            except Exception as e:
                if "timeout" not in str(e).lower():
                    print(f"   ❌ Ошибка: {e}")

print("\n" + "=" * 50)

if not found_bot:
    print("❌ НЕ НАЙДЕН рабочий бот на стандартных путях")
    print("\n💡 ВОЗМОЖНЫЕ ПРИЧИНЫ:")
    print("   1. Сервис не запущен на Railway")
    print("   2. Ошибка в деплойменте")
    print("   3. Другой домен/порт")
    print("   4. Требуется перезапуск сервиса")
    
    print("\n🔧 РЕКОМЕНДАЦИИ:")
    print("   1. Проверьте Railway Dashboard - статус деплоя")
    print("   2. Посмотрите логи Railway") 
    print("   3. Попробуйте ручной редеплой")
    print("   4. Проверьте переменные окружения")
else:
    print("✅ Бот найден!")