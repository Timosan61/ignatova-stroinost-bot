"""
Voice Service Module для ignatova-stroinost-bot

Модуль для обработки голосовых сообщений с использованием OpenAI Whisper.
"""

from .voice_service import VoiceService
from .config import (
    MAX_AUDIO_SIZE_MB,
    MAX_AUDIO_DURATION_SECONDS,
    SUPPORTED_AUDIO_FORMATS,
    WHISPER_LANGUAGE
)

__all__ = [
    'VoiceService',
    'MAX_AUDIO_SIZE_MB',
    'MAX_AUDIO_DURATION_SECONDS',
    'SUPPORTED_AUDIO_FORMATS',
    'WHISPER_LANGUAGE'
]