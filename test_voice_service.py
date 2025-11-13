#!/usr/bin/env python3
"""
Тест VoiceService
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_voice_service():
    """Тестируем VoiceService"""
    print("🔊 Тестируем VoiceService...")
    
    try:
        from bot.voice.voice_service import VoiceService
        print("✅ VoiceService успешно импортирован")
        
        # Проверяем инициализацию
        voice_service = VoiceService()
        print("✅ VoiceService успешно инициализирован")
        
        return True
        
    except ImportError as e:
        print(f"❌ Ошибка импорта VoiceService: {e}")
        return False
    except Exception as e:
        print(f"❌ Ошибка инициализации VoiceService: {e}")
        return False

def test_voice_dependencies():
    """Тестируем зависимости для голосовых сообщений"""
    print("🔍 Проверяем зависимости...")
    
    dependencies = [
        ('openai', 'OpenAI API'),
        ('requests', 'HTTP requests')
    ]
    
    all_ok = True
    for module, desc in dependencies:
        try:
            __import__(module)
            print(f"✅ {desc}: доступен")
        except ImportError:
            print(f"❌ {desc}: отсутствует")
            all_ok = False
    
    return all_ok

if __name__ == "__main__":
    print("🧪 Тестирование голосового сервиса")
    
    deps_ok = test_voice_dependencies()
    voice_ok = test_voice_service()
    
    if deps_ok and voice_ok:
        print("\n✅ Все тесты пройдены - голосовые сообщения должны работать")
    else:
        print("\n❌ Есть проблемы с голосовыми сообщениями")