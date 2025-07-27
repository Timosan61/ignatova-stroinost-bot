#!/usr/bin/env python3
"""
Тест извлечения file_id из разных структур голосовых данных
"""

import asyncio
import sys
import os
sys.path.append('.')

async def test_file_id_extraction():
    """Тестирует извлечение file_id из разных структур данных"""
    
    print("=== ТЕСТ ИЗВЛЕЧЕНИЯ FILE_ID ===")
    
    # Импортируем функцию из webhook
    import webhook
    
    # Тестовые данные как они приходят из Telegram
    test_cases = [
        {
            "name": "Голосовое сообщение (voice)",
            "data": {
                'file_id': 'AwACAgIAAxkBAAICumY1234567890abcdefghijklmnop',
                'file_unique_id': 'AgADCgAB1234567890',
                'duration': 3,
                'file_size': 12345
            }
        },
        {
            "name": "Аудио сообщение (audio) - как приходит из msg.get('audio')",
            "data": {
                'file_id': 'CQACAgIAAxkBAAICumY1234567890abcdefghijklmnop',
                'file_unique_id': 'AgADCgAB1234567890', 
                'duration': 5,
                'file_size': 23456,
                'performer': 'Test Artist',
                'title': 'Test Song'
            }
        },
        {
            "name": "Аудио документ (document)",
            "data": {
                'file_id': 'BQACAgIAAxkBAAICumY1234567890abcdefghijklmnop',
                'file_unique_id': 'AgADCgAB1234567890',
                'file_name': 'voice_message.ogg',
                'mime_type': 'audio/ogg',
                'file_size': 34567
            }
        },
        {
            "name": "Неправильная структура с вложенным audio",
            "data": {
                'audio': {
                    'file_id': 'CQACAgIAAxkBAAICumY1234567890abcdefghijklmnop',
                    'duration': 5,
                    'file_size': 23456
                }
            }
        }
    ]
    
    for test_case in test_cases:
        print(f"\n🔄 Тестируем: {test_case['name']}")
        data = test_case['data']
        print(f"📋 Входные данные: {data}")
        
        try:
            # Тестируем нашу функцию извлечения
            result = await webhook.process_voice_transcription(data, 12345)
            
            print(f"✅ Результат: success={result.get('success')}, error={result.get('error')}")
            
        except Exception as e:
            print(f"❌ Ошибка: {e}")
    
    print(f"\n✅ Тест завершен")

if __name__ == "__main__":
    asyncio.run(test_file_id_extraction())