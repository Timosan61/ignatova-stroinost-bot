#!/usr/bin/env python3
"""
Диагностика проблемы с VOICE_ENABLED на Railway
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_voice_config():
    """Тестируем конфигурацию голосовых сообщений"""
    print("🔍 Тестируем конфигурацию VOICE_ENABLED...")
    
    # Симулируем Railway окружение
    test_cases = [
        ("true", "Переменная VOICE_ENABLED=true"),
        ("True", "Переменная VOICE_ENABLED=True"), 
        ("1", "Переменная VOICE_ENABLED=1"),
        ("false", "Переменная VOICE_ENABLED=false"),
        ("", "Переменная VOICE_ENABLED пустая"),
        (None, "Переменная VOICE_ENABLED отсутствует")
    ]
    
    for value, description in test_cases:
        print(f"\n📋 {description}:")
        
        # Устанавливаем переменную
        if value is not None:
            os.environ['VOICE_ENABLED'] = value
        elif 'VOICE_ENABLED' in os.environ:
            del os.environ['VOICE_ENABLED']
            
        # Импортируем заново config
        if 'bot.config' in sys.modules:
            del sys.modules['bot.config']
        
        try:
            from bot.config import VOICE_ENABLED
            print(f"  Результат VOICE_ENABLED: {VOICE_ENABLED} (тип: {type(VOICE_ENABLED)})")
        except Exception as e:
            print(f"  Ошибка: {e}")

def test_agent_voice_initialization():
    """Тестируем инициализацию голосового сервиса в агенте"""
    print("\n🤖 Тестируем инициализацию агента с VOICE_ENABLED=true...")
    
    # Устанавливаем VOICE_ENABLED=true
    os.environ['VOICE_ENABLED'] = 'true'
    
    # Очищаем кэшированные модули
    modules_to_clear = [mod for mod in sys.modules.keys() if mod.startswith('bot.')]
    for mod in modules_to_clear:
        del sys.modules[mod]
    
    try:
        from bot.agent import TextilProAgent
        agent = TextilProAgent()
        
        print(f"✅ Агент создан")
        print(f"  hasattr voice_service: {hasattr(agent, 'voice_service')}")
        print(f"  voice_service не None: {bool(agent.voice_service) if hasattr(agent, 'voice_service') else False}")
        print(f"  voice_service тип: {type(agent.voice_service) if hasattr(agent, 'voice_service') and agent.voice_service else None}")
        
    except Exception as e:
        print(f"❌ Ошибка создания агента: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_voice_config()
    test_agent_voice_initialization()