"""
Whisper Client - интеграция с OpenAI Whisper API для транскрипции аудио
Адаптированный для ignatova-stroinost-bot
"""

import os
import logging
from typing import Optional, Dict, Any
from pathlib import Path

import openai
from openai import AsyncOpenAI

from .config import (
    WHISPER_MODEL, WHISPER_RESPONSE_FORMAT, WHISPER_LANGUAGE,
    WHISPER_TIMEOUT_SECONDS, SUPPORTED_AUDIO_FORMATS
)

logger = logging.getLogger(__name__)


class WhisperTranscriber:
    """Класс для транскрипции аудио через OpenAI Whisper API"""
    
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("OpenAI API key is required for Whisper transcription")
        
        self.client = AsyncOpenAI(
            api_key=api_key,
            timeout=WHISPER_TIMEOUT_SECONDS
        )
    
    async def transcribe(self, audio_file_path: str, language: Optional[str] = None) -> Dict[str, Any]:
        """
        Транскрибирует аудио файл в текст
        
        Args:
            audio_file_path: Путь к аудио файлу
            language: Язык аудио (опционально, по умолчанию русский)
        
        Returns:
            Dict с результатом транскрипции
        """
        try:
            # Валидация файла
            validation_result = self.validate_audio_file(audio_file_path)
            if not validation_result["valid"]:
                logger.error(f"❌ Файл не прошел валидацию: {validation_result['error']}")
                return {
                    "success": False,
                    "error": validation_result["error"],
                    "text": None
                }
            
            # Подготавливаем параметры для Whisper
            transcription_params = {
                "model": WHISPER_MODEL,
                "response_format": WHISPER_RESPONSE_FORMAT
            }
            
            # Добавляем язык если указан
            target_language = language or WHISPER_LANGUAGE
            if target_language:
                transcription_params["language"] = target_language
            
            logger.info(f"🎤 Начинаем транскрипцию файла: {audio_file_path}")
            logger.debug(f"📋 Параметры Whisper: {transcription_params}")
            
            # Открываем и отправляем файл в Whisper
            with open(audio_file_path, "rb") as audio_file:
                transcript = await self.client.audio.transcriptions.create(
                    file=audio_file,
                    **transcription_params
                )
            
            # Обрабатываем результат
            if isinstance(transcript, str):
                # Простой текстовый ответ
                transcribed_text = transcript.strip()
            else:
                # JSON ответ
                transcribed_text = getattr(transcript, 'text', '').strip()
            
            if transcribed_text:
                logger.info(f"✅ Транскрипция успешна: {len(transcribed_text)} символов")
                logger.debug(f"📝 Транскрибированный текст: {transcribed_text[:100]}...")
                
                return {
                    "success": True,
                    "text": transcribed_text,
                    "language": target_language,
                    "file_path": audio_file_path,
                    "char_count": len(transcribed_text)
                }
            else:
                logger.warning("⚠️ Whisper вернул пустой результат")
                return {
                    "success": False,
                    "error": "Empty transcription result",
                    "text": None
                }
                
        except openai.APIError as e:
            logger.error(f"❌ OpenAI API ошибка: {e}")
            return {
                "success": False,
                "error": f"OpenAI API error: {str(e)}",
                "text": None
            }
        except Exception as e:
            logger.error(f"❌ Ошибка транскрипции: {e}")
            return {
                "success": False,
                "error": f"Transcription error: {str(e)}",
                "text": None
            }
    
    def validate_audio_file(self, file_path: str) -> Dict[str, Any]:
        """
        Валидирует аудио файл перед отправкой в Whisper
        
        Returns:
            Dict с результатом валидации: {"valid": bool, "error": str}
        """
        try:
            # Проверяем существование файла
            if not os.path.exists(file_path):
                return {"valid": False, "error": f"File not found: {file_path}"}
            
            # Проверяем что это файл
            if not os.path.isfile(file_path):
                return {"valid": False, "error": f"Path is not a file: {file_path}"}
            
            # Проверяем размер файла
            file_size = os.path.getsize(file_path)
            if file_size == 0:
                return {"valid": False, "error": "File is empty"}
            
            # Проверяем расширение файла
            file_extension = Path(file_path).suffix.lower().lstrip('.')
            if file_extension not in SUPPORTED_AUDIO_FORMATS:
                return {
                    "valid": False, 
                    "error": f"Unsupported format: {file_extension}. Supported: {SUPPORTED_AUDIO_FORMATS}"
                }
            
            logger.debug(f"✅ Файл прошел валидацию: {file_path} ({file_size} bytes, .{file_extension})")
            return {"valid": True, "error": None}
            
        except Exception as e:
            return {"valid": False, "error": f"Validation error: {str(e)}"}
    
    def get_supported_formats(self) -> list:
        """Возвращает список поддерживаемых форматов"""
        return SUPPORTED_AUDIO_FORMATS.copy()
    
    async def test_connection(self) -> bool:
        """Тестирует подключение к OpenAI API"""
        try:
            # Пытаемся получить список моделей для проверки API ключа
            models = await self.client.models.list()
            if models:
                logger.info("✅ Подключение к OpenAI API успешно")
                return True
            else:
                logger.error("❌ Не удалось получить список моделей")
                return False
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к OpenAI API: {e}")
            return False