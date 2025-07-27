#!/usr/bin/env python3
"""
Скрипт для отладки голосовых сообщений
"""

import asyncio
import sys
import os
sys.path.append('.')

async def test_voice_debug():
    """Тестирует различные структуры голосовых данных"""
    
    try:
        from bot.agent import agent
        
        print("=== ТЕСТ РАЗЛИЧНЫХ ФОРМАТОВ ГОЛОСОВЫХ ДАННЫХ ===")
        
        # Тест 1: Стандартное голосовое сообщение
        test_voice_1 = {
            'file_id': 'AwACAgIAAxkBAAICumY1234567890abcdefghijklmnop',
            'file_unique_id': 'AgADCgAB1234567890',
            'duration': 3,
            'file_size': 12345
        }
        
        # Тест 2: Аудио сообщение
        test_voice_2 = {
            'audio': {
                'file_id': 'CQACAgIAAxkBAAICumY1234567890abcdefghijklmnop',
                'file_unique_id': 'AgADCgAB1234567890',
                'duration': 5,
                'file_size': 23456
            }
        }
        
        # Тест 3: Документ с аудио
        test_voice_3 = {
            'file_id': 'BQACAgIAAxkBAAICumY1234567890abcdefghijklmnop',
            'file_unique_id': 'AgADCgAB1234567890',
            'file_name': 'voice_message.ogg',
            'mime_type': 'audio/ogg',
            'file_size': 34567
        }
        
        test_cases = [
            ("Стандартное голосовое", test_voice_1),
            ("Аудио сообщение", test_voice_2),
            ("Аудио документ", test_voice_3)
        ]
        
        for test_name, test_data in test_cases:
            print(f"\n🔄 Тестируем: {test_name}")
            print(f"📋 Данные: {test_data}")
            
            try:
                # Тестируем только извлечение file_id и базовую валидацию
                from bot.voice.voice_service import VoiceService
                
                # Теперь voice_service находится в webhook
                print("  ℹ️ Голосовой сервис теперь находится в webhook.py, а не в agent")
                try:
                    import webhook
                    vs = webhook.voice_service
                except:
                    vs = None
                    
                if vs:
                    # Симулируем начало process_voice_message
                    file_id = test_data.get('file_id')
                    if not file_id:
                        file_id = test_data.get('file_id') or test_data.get('audio', {}).get('file_id')
                    
                    duration = test_data.get('duration', 0)
                    if not duration and test_data.get('audio'):
                        duration = test_data.get('audio', {}).get('duration', 0)
                    
                    file_size = test_data.get('file_size', 0)
                    if not file_size and test_data.get('audio'):
                        file_size = test_data.get('audio', {}).get('file_size', 0)
                    
                    print(f"  🔑 file_id: {file_id}")
                    print(f"  🕐 duration: {duration}с")
                    print(f"  📊 file_size: {file_size} bytes")
                    
                    if file_id:
                        print(f"  ✅ file_id извлечен успешно")
                    else:
                        print(f"  ❌ file_id не найден")
                        
                else:
                    print("  ❌ Голосовой сервис не инициализирован")
                    
            except Exception as e:
                print(f"  ❌ Ошибка при тестировании: {e}")
        
        print("\n=== ОБЩАЯ ИНФОРМАЦИЯ О СЕРВИСЕ ===")
        
        # Проверяем voice_service из webhook
        try:
            import webhook
            voice_service = webhook.voice_service
            
            if voice_service:
                service_info = voice_service.get_service_info()
                test_results = await voice_service.test_service()
                
                print(f"✅ Voice service найден в webhook")
                print(f"Сервис готов: {test_results.get('service_ready', False)}")
                print(f"Whisper подключение: {test_results.get('whisper_connection', False)}")
                print(f"Поддерживаемые форматы: {service_info.get('supported_formats', [])}")
            else:
                print("❌ Голосовой сервис не инициализирован в webhook")
        except Exception as e:
            print(f"❌ Ошибка проверки webhook voice service: {e}")
            print("❌ Голосовой сервис недоступен")
                        
    except Exception as e:
        print(f"❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_voice_debug())