#!/usr/bin/env python3
"""
Тест голосового сервиса с реальными данными
"""

import asyncio
import sys
import os
import traceback
sys.path.append('.')

async def test_voice_with_real_data():
    """Тестирует голосовой сервис с реальными данными"""
    
    try:
        # Инициализируем голосовой сервис
        from bot.voice.voice_service import VoiceService
        from bot.config import TELEGRAM_BOT_TOKEN, OPENAI_API_KEY
        
        print("=== ТЕСТ РЕАЛЬНОГО ГОЛОСОВОГО СЕРВИСА ===")
        print(f"🔑 TELEGRAM_BOT_TOKEN: {'✅' if TELEGRAM_BOT_TOKEN else '❌'}")
        print(f"🔑 OPENAI_API_KEY: {'✅' if OPENAI_API_KEY else '❌'}")
        
        if not TELEGRAM_BOT_TOKEN:
            print("❌ TELEGRAM_BOT_TOKEN не найден")
            return
            
        if not OPENAI_API_KEY:
            print("❌ OPENAI_API_KEY не найден")
            return
        
        voice_service = VoiceService(TELEGRAM_BOT_TOKEN, OPENAI_API_KEY)
        
        # Проверяем сервис
        service_info = voice_service.get_service_info()
        test_results = await voice_service.test_service()
        
        print(f"\n📊 Информация о сервисе:")
        print(f"• Статус: {service_info['status']}")
        print(f"• Telegram токен: {'✅' if test_results['telegram_token'] else '❌'}")
        print(f"• OpenAI ключ: {'✅' if test_results['openai_key'] else '❌'}")
        print(f"• Whisper клиент: {'✅' if test_results['whisper_client'] else '❌'}")
        print(f"• Whisper подключение: {'✅' if test_results['whisper_connection'] else '❌'}")
        print(f"• Сервис готов: {'✅' if test_results['service_ready'] else '❌'}")
        
        if not test_results['service_ready']:
            print("❌ Сервис не готов к работе")
            if not test_results['whisper_connection']:
                print("   ⚠️ Проблема с подключением к Whisper API")
            return
        
        # Тестируем с некорректным file_id
        print(f"\n🎤 Тестируем с некорректным file_id...")
        test_voice_data = {
            'file_id': 'invalid_file_id_test',
            'duration': 3,
            'file_size': 1000
        }
        
        try:
            result = await voice_service.transcribe_voice_message(
                test_voice_data, "test_user", "test_msg"
            )
            
            print(f"📋 Результат:")
            print(f"• Успех: {result.get('success', False)}")
            print(f"• Текст: {result.get('text', 'None')}")
            print(f"• Ошибка: {result.get('error', 'None')}")
            
        except Exception as e:
            print(f"❌ Исключение при тестировании: {e}")
            print(f"📄 Трейс: {traceback.format_exc()}")
        
        # Проверяем также процесс скачивания файла
        print(f"\n📥 Тестируем скачивание файла...")
        from bot.voice.telegram_audio import TelegramAudioDownloader
        
        try:
            async with TelegramAudioDownloader(TELEGRAM_BOT_TOKEN) as downloader:
                # Получаем информацию о файле  
                file_info = await downloader.get_file_info('invalid_file_id_test')
                print(f"📄 Информация о файле: {file_info}")
                
        except Exception as e:
            print(f"❌ Ошибка скачивания: {e}")
            
        print(f"\n✅ Тест завершен")
        
    except Exception as e:
        print(f"❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_voice_with_real_data())