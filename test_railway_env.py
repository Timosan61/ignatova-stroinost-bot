#!/usr/bin/env python3
"""
Тест переменных окружения через Railway webhook
"""
import requests
import json

def test_railway_bot():
    """Тестирование бота на Railway"""
    base_url = "https://ignatova-stroinost-bot-production.up.railway.app"
    
    print("🔍 Тестируем Railway бота...")
    
    # Проверяем основной статус
    try:
        response = requests.get(f"{base_url}/")
        if response.status_code == 200:
            data = response.json()
            print("\n📊 Статус бота:")
            print(f"  AI Status: {data.get('ai_status', 'unknown')}")
            print(f"  OpenAI: {data.get('openai_configured', 'unknown')}")
            print(f"  Anthropic: {data.get('anthropic_configured', 'unknown')}")
            print(f"  Voice: {data.get('voice_status', 'unknown')}")
            print(f"  Zep: {data.get('zep_status', 'unknown')}")
        else:
            print(f"❌ Ошибка получения статуса: {response.status_code}")
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
    
    # Проверяем health endpoint
    try:
        response = requests.get(f"{base_url}/health")
        if response.status_code == 200:
            data = response.json()
            print(f"\n🔋 Health check:")
            print(f"  AI Enabled: {data.get('ai_enabled', 'unknown')}")
            print(f"  Components: {data.get('components', {})}")
        else:
            print(f"❌ Health check failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Health check error: {e}")
        
    # Пробуем новый debug endpoint
    try:
        response = requests.get(f"{base_url}/debug/env")
        if response.status_code == 200:
            data = response.json()
            print(f"\n🐛 Debug info:")
            print(f"  Env vars: {data.get('env_vars', {})}")
            print(f"  AI enabled: {data.get('ai_enabled', 'unknown')}")
            print(f"  Agent initialized: {data.get('agent_initialized', 'unknown')}")
        else:
            print(f"⚠️ Debug endpoint not available: {response.status_code}")
    except Exception as e:
        print(f"⚠️ Debug endpoint error: {e}")

    print(f"\n🔗 Доступные endpoints:")
    print(f"  Main: {base_url}/")
    print(f"  Health: {base_url}/health")
    print(f"  Webhook Info: {base_url}/webhook/info")

if __name__ == "__main__":
    test_railway_bot()