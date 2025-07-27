"""
Конфигурация для Voice Service модуля ignatova-stroinost-bot
"""

import os
import tempfile
from pathlib import Path

# Папка для временных аудио файлов
TEMP_AUDIO_DIR = os.path.join(tempfile.gettempdir(), "ignatova_voice")

# Максимальный размер аудио файла (25MB - лимит OpenAI Whisper)
MAX_AUDIO_SIZE_MB = 25
MAX_AUDIO_SIZE_BYTES = MAX_AUDIO_SIZE_MB * 1024 * 1024

# Максимальная длительность аудио (для безопасности)
MAX_AUDIO_DURATION_SECONDS = 600  # 10 минут

# Поддерживаемые форматы аудио для Whisper
SUPPORTED_AUDIO_FORMATS = [
    'mp3', 'mp4', 'mpeg', 'mpga', 'm4a', 'wav', 'webm', 'oga'
]

# Настройки Telegram Bot API
TELEGRAM_API_BASE_URL = "https://api.telegram.org/bot{token}/{method}"
TELEGRAM_FILE_BASE_URL = "https://api.telegram.org/file/bot{token}/{file_path}"

# Настройки Whisper API
WHISPER_MODEL = "whisper-1"
WHISPER_RESPONSE_FORMAT = "text"  # или "json", "srt", "verbose_json", "vtt"
WHISPER_LANGUAGE = "ru"  # Русский язык по умолчанию для ignatova-stroinost

# Настройки таймаутов
DOWNLOAD_TIMEOUT_SECONDS = 30
WHISPER_TIMEOUT_SECONDS = 60

# Логирование
VOICE_LOG_LEVEL = os.getenv('VOICE_LOG_LEVEL', 'DEBUG')

# Создаем временную папку если её нет
def ensure_temp_dir():
    """Создает временную папку для аудио файлов"""
    Path(TEMP_AUDIO_DIR).mkdir(parents=True, exist_ok=True)
    return TEMP_AUDIO_DIR