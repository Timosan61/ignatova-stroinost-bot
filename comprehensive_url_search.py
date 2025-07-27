#!/usr/bin/env python3
"""
Полный поиск URL Railway для ignatova-stroinost-bot
"""
import requests
import string
import itertools

def generate_railway_variations():
    """Генерирует возможные варианты Railway URL"""
    
    # Базовые имена проекта
    project_names = [
        "ignatova-stroinost-bot",
        "ignatova-stroinost-bot-production", 
        "ignatova-bot",
        "stroinost-bot",
        "textilebot",
        "textile-bot"
    ]
    
    # Домены Railway
    domains = [
        "up.railway.app",
        "railway.app"
    ]
    
    urls = []
    
    # Генерируем основные URL
    for name in project_names:
        for domain in domains:
            urls.append(f"https://{name}.{domain}")
    
    # web-production-XXXX формат
    # Попробуем разные комбинации
    hex_chars = '0123456789abcdef'
    for combo in itertools.product(hex_chars, repeat=4):
        code = ''.join(combo)
        urls.append(f"https://web-production-{code}.up.railway.app")
        # Ограничиваем до первых 20 для экономии времени
        if len([u for u in urls if 'web-production' in u]) >= 20:
            break
    
    return urls

def check_url(url, timeout=3):
    """Проверяет URL и возвращает информацию"""
    try:
        response = requests.get(url, timeout=timeout)
        
        result = {
            'url': url,
            'status': response.status_code,
            'working': False,
            'is_bot': False,
            'content_preview': ''
        }
        
        if response.status_code == 200:
            result['working'] = True
            
            # Проверяем содержимое
            try:
                data = response.json()
                result['content_preview'] = str(data)[:200]
                
                # Проверяем признаки нашего бота
                if any(key in data for key in ['status', 'bot', 'ignatova', 'textile']):
                    result['is_bot'] = True
                    
            except:
                content = response.text[:200]
                result['content_preview'] = content
                
                # Проверяем текстовый контент
                bot_indicators = ['ignatova', 'textile', 'stroinost', 'bot', 'webhook']
                if any(indicator in content.lower() for indicator in bot_indicators):
                    result['is_bot'] = True
        
        return result
        
    except Exception as e:
        return {
            'url': url,
            'status': 'error',
            'working': False,
            'is_bot': False,
            'error': str(e)
        }

def main():
    print("🔍 ПОЛНЫЙ ПОИСК Railway URL для ignatova-stroinost-bot")
    print("=" * 60)
    
    urls = generate_railway_variations()
    print(f"💫 Проверяем {len(urls)} URL вариантов...")
    print()
    
    working_urls = []
    bot_urls = []
    
    # Сначала проверим приоритетные URL
    priority_urls = [
        "https://ignatova-stroinost-bot.up.railway.app",
        "https://ignatova-stroinost-bot-production.up.railway.app",
        f"https://web-production-472c.up.railway.app"  # Из старых логов
    ]
    
    print("🎯 ПРИОРИТЕТНЫЕ URL:")
    for url in priority_urls:
        print(f"   Проверяем: {url}")
        result = check_url(url, timeout=10)
        
        if result['working']:
            working_urls.append(result)
            print(f"   ✅ Работает! Статус: {result['status']}")
            print(f"   📋 Содержимое: {result['content_preview']}")
            
            if result['is_bot']:
                bot_urls.append(result)
                print(f"   🤖 ПОХОЖЕ НА НАШ БОТ!")
        else:
            print(f"   ❌ Не работает: {result.get('error', result['status'])}")
        print()
    
    if bot_urls:
        print("🎉 НАЙДЕНЫ РАБОЧИЕ URL БОТА!")
        for result in bot_urls:
            print(f"   ✅ {result['url']}")
            print(f"      └─ Webhook: {result['url']}/webhook")
        return bot_urls[0]['url']
    
    # Если не найден в приоритетных, продолжаем поиск
    print("🔍 РАСШИРЕННЫЙ ПОИСК...")
    
    batch_size = 10
    for i in range(0, min(len(urls), 50), batch_size):  # Ограничиваем поиск
        batch = urls[i:i + batch_size]
        print(f"\n📦 Пакет {i//batch_size + 1}: проверяем {len(batch)} URL...")
        
        for url in batch:
            if url in [u['url'] for u in working_urls]:  # Пропускаем уже проверенные
                continue
                
            result = check_url(url)
            
            if result['working']:
                working_urls.append(result)
                print(f"   ✅ {url} - работает!")
                
                if result['is_bot']:
                    bot_urls.append(result)
                    print(f"   🤖 НАЙДЕН БОТ: {url}")
                    return url
    
    print("\n" + "=" * 60)
    print("📊 ИТОГИ ПОИСКА:")
    
    if bot_urls:
        print(f"🎉 НАЙДЕНО {len(bot_urls)} URL с ботом:")
        for result in bot_urls:
            print(f"   🤖 {result['url']}")
        return bot_urls[0]['url']
    
    elif working_urls:
        print(f"⚠️ Найдено {len(working_urls)} рабочих URL (но не боты):")
        for result in working_urls:
            print(f"   ✅ {result['url']} - {result['content_preview'][:50]}...")
        print("\n💡 Возможно бот работает по одному из этих URL")
        return working_urls[0]['url']
    
    else:
        print("❌ НЕ НАЙДЕНО рабочих URL!")
        print("\n💡 ВОЗМОЖНЫЕ ПРИЧИНЫ:")
        print("   1. Сервис не запущен на Railway")
        print("   2. Нестандартный формат URL")
        print("   3. Проблемы с деплоем")
        print("\n🔧 РЕКОМЕНДАЦИИ:")
        print("   1. Проверьте Railway Dashboard")
        print("   2. Проверьте логи деплоя")
        print("   3. Попробуйте ручной поиск в Railway")
        return None

if __name__ == "__main__":
    found_url = main()
    if found_url:
        print(f"\n🎯 РЕКОМЕНДУЕМЫЙ WEBHOOK URL:")
        print(f"   {found_url}/webhook")
    else:
        print(f"\n⚠️ ТРЕБУЕТСЯ РУЧНАЯ ПРОВЕРКА Railway Dashboard")