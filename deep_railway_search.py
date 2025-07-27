#!/usr/bin/env python3
"""
Глубокий поиск Railway URL для бота
"""
import requests
import json

def test_bot_endpoint(url):
    """Тестирует является ли URL нашим ботом"""
    try:
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            # Проверяем JSON ответ
            try:
                data = response.json()
                # Ищем признаки нашего бота
                if isinstance(data, dict):
                    content = json.dumps(data).lower()
                    bot_indicators = ['ignatova', 'textile', 'stroinost', 'bot', 'status', 'openai', 'zep']
                    score = sum(1 for indicator in bot_indicators if indicator in content)
                    
                    if score >= 2:
                        return {
                            'url': url,
                            'status': 'BOT_FOUND',
                            'score': score,
                            'data': data,
                            'indicators': [i for i in bot_indicators if i in content]
                        }
                        
            except json.JSONDecodeError:
                # Проверяем HTML/текст
                content = response.text.lower()
                bot_indicators = ['ignatova', 'textile', 'stroinost', 'webhook', 'fastapi']
                score = sum(1 for indicator in bot_indicators if indicator in content)
                
                if score >= 1:
                    return {
                        'url': url,
                        'status': 'POSSIBLE_BOT',
                        'score': score,
                        'content_preview': response.text[:300],
                        'indicators': [i for i in bot_indicators if i in content]
                    }
        
        return {
            'url': url,
            'status': f'HTTP_{response.status_code}',
            'content_preview': response.text[:100] if response.text else 'Empty'
        }
        
    except Exception as e:
        return {
            'url': url,
            'status': 'ERROR',
            'error': str(e)
        }

def main():
    print("🔍 ГЛУБОКИЙ ПОИСК Railway URL для ignatova-stroinost-bot")
    print("=" * 60)
    
    # Возможные домены Railway
    base_domains = [
        "railway.app",
        "up.railway.app",
        "railway.com"
    ]
    
    # Возможные префиксы
    prefixes = [
        "ignatova-stroinost-bot",
        "ignatova-stroinost-bot-production",
        "ignatova-bot",
        "stroinost-bot",
        "textilebot",
        "textile-bot",
        "production",
        "web-production-472c",  # Из старых логов
    ]
    
    # Генерируем URL для тестирования
    test_urls = []
    
    for domain in base_domains:
        for prefix in prefixes:
            test_urls.append(f"https://{prefix}.{domain}")
    
    # Добавляем специальные варианты
    special_urls = [
        "https://web-production-472c.up.railway.app",
        "https://ignatova-stroinost-bot.railway.internal",  # Внутренний URL
    ]
    test_urls.extend(special_urls)
    
    print(f"🧪 Тестируем {len(test_urls)} URL вариантов...")
    print()
    
    results = []
    bot_candidates = []
    
    for i, url in enumerate(test_urls, 1):
        print(f"[{i:2d}/{len(test_urls)}] Тестируем: {url}")
        
        result = test_bot_endpoint(url)
        results.append(result)
        
        if result['status'] in ['BOT_FOUND', 'POSSIBLE_BOT']:
            bot_candidates.append(result)
            print(f"   🎯 {result['status']}: Score {result.get('score', 0)}")
            print(f"   📋 Индикаторы: {result.get('indicators', [])}")
            
        elif result['status'].startswith('HTTP_2'):
            print(f"   ✅ Доступен: {result['status']}")
            
        elif result['status'] == 'ERROR':
            if 'timeout' not in result.get('error', '').lower():
                print(f"   ❌ Ошибка: {result['error']}")
        else:
            print(f"   ⚠️ {result['status']}")
    
    print("\n" + "=" * 60)
    print("📊 РЕЗУЛЬТАТЫ ПОИСКА:")
    
    if bot_candidates:
        print(f"\n🎉 НАЙДЕНО {len(bot_candidates)} кандидатов бота:")
        
        for candidate in sorted(bot_candidates, key=lambda x: x.get('score', 0), reverse=True):
            print(f"\n🤖 {candidate['url']}")
            print(f"   Статус: {candidate['status']}")
            print(f"   Рейтинг: {candidate.get('score', 0)}/7")
            print(f"   Индикаторы: {candidate.get('indicators', [])}")
            
            if 'data' in candidate:
                print(f"   JSON данные: {candidate['data']}")
            elif 'content_preview' in candidate:
                print(f"   Превью: {candidate['content_preview'][:100]}...")
                
        # Рекомендуем лучший кандидат
        best = bot_candidates[0]
        print(f"\n🎯 РЕКОМЕНДУЕМЫЙ URL: {best['url']}")
        print(f"   Webhook: {best['url']}/webhook")
        
    else:
        print("\n❌ БОТЫ НЕ НАЙДЕНЫ!")
        
        # Показываем доступные URL
        working_urls = [r for r in results if r['status'].startswith('HTTP_2')]
        if working_urls:
            print(f"\n✅ Найдено {len(working_urls)} доступных URL:")
            for result in working_urls[:5]:  # Показываем первые 5
                print(f"   - {result['url']} ({result['status']})")
        
        print(f"\n💡 ВОЗМОЖНЫЕ ПРИЧИНЫ:")
        print(f"   1. Сервис не запущен или недоступен")
        print(f"   2. Используется нестандартный порт или путь")  
        print(f"   3. Проблемы с Railway конфигурацией")
        print(f"   4. Сервис работает только внутри Railway сети")
        
        print(f"\n🔧 РЕКОМЕНДАЦИИ:")
        print(f"   1. Проверьте Railway Dashboard - статус сервиса")
        print(f"   2. Проверьте railway.json конфигурацию")
        print(f"   3. Попробуйте ручной редеплой")
        print(f"   4. Проверьте логи Railway на ошибки")

if __name__ == "__main__":
    main()