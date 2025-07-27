"""
Telegram Audio Downloader - скачивание голосовых сообщений через Telegram Bot API
Адаптированный для ignatova-stroinost-bot
"""

import os
import asyncio
import logging
import aiohttp
import aiofiles
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from .config import (
    TELEGRAM_API_BASE_URL, TELEGRAM_FILE_BASE_URL, 
    TEMP_AUDIO_DIR, MAX_AUDIO_SIZE_BYTES, 
    DOWNLOAD_TIMEOUT_SECONDS, ensure_temp_dir
)

logger = logging.getLogger(__name__)


class TelegramAudioDownloader:
    """Класс для скачивания аудио файлов из Telegram"""
    
    def __init__(self, bot_token: str):
        self.bot_token = bot_token
        self.session: Optional[aiohttp.ClientSession] = None
        ensure_temp_dir()
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=DOWNLOAD_TIMEOUT_SECONDS)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def get_file_info(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Получает информацию о файле через Telegram Bot API"""
        try:
            url = TELEGRAM_API_BASE_URL.format(
                token=self.bot_token, 
                method="getFile"
            )
            
            async with self.session.post(url, json={"file_id": file_id}) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("ok"):
                        file_info = data.get("result", {})
                        logger.info(f"✅ Получена информация о файле {file_id}: {file_info.get('file_size')} bytes")
                        return file_info
                    else:
                        logger.error(f"❌ Telegram API ошибка: {data.get('description')}")
                        return None
                else:
                    logger.error(f"❌ HTTP ошибка при получении файла: {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"❌ Ошибка при получении информации о файле {file_id}: {e}")
            return None
    
    async def download_voice_file(self, file_id: str, voice_data: Dict[str, Any]) -> Optional[str]:
        """
        Скачивает голосовой файл по file_id
        Возвращает путь к скачанному файлу или None при ошибке
        """
        try:
            # Проверяем размер файла
            file_size = voice_data.get('file_size', 0)
            if file_size > MAX_AUDIO_SIZE_BYTES:
                logger.error(f"❌ Файл слишком большой: {file_size} bytes (макс. {MAX_AUDIO_SIZE_BYTES})")
                return None
            
            # Получаем информацию о файле
            file_info = await self.get_file_info(file_id)
            if not file_info:
                return None
            
            file_path = file_info.get('file_path')
            if not file_path:
                logger.error("❌ file_path не найден в ответе Telegram API")
                return None
            
            # Формируем URL для скачивания
            download_url = TELEGRAM_FILE_BASE_URL.format(
                token=self.bot_token,
                file_path=file_path
            )
            
            # Создаем уникальное имя файла
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            duration = voice_data.get('duration', 0)
            file_extension = self._get_file_extension(file_path)
            local_filename = f"voice_{timestamp}_{duration}s_{file_id[:8]}.{file_extension}"
            local_path = os.path.join(TEMP_AUDIO_DIR, local_filename)
            
            # Скачиваем файл
            logger.info(f"📥 Скачиваем голосовой файл: {download_url}")
            async with self.session.get(download_url) as response:
                if response.status == 200:
                    async with aiofiles.open(local_path, 'wb') as f:
                        async for chunk in response.content.iter_chunked(8192):
                            await f.write(chunk)
                    
                    # Проверяем что файл скачался
                    if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
                        logger.info(f"✅ Файл скачан: {local_path} ({os.path.getsize(local_path)} bytes)")
                        return local_path
                    else:
                        logger.error(f"❌ Файл не скачался или пустой: {local_path}")
                        return None
                else:
                    logger.error(f"❌ Ошибка скачивания файла: HTTP {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"❌ Ошибка при скачивании файла {file_id}: {e}")
            return None
    
    def _get_file_extension(self, file_path: str) -> str:
        """Определяет расширение файла из пути"""
        if not file_path:
            return "oga"  # По умолчанию для голосовых Telegram
        
        extension = Path(file_path).suffix.lstrip('.')
        if not extension:
            return "oga"
        
        return extension
    
    @staticmethod
    def cleanup_temp_files(older_than_hours: int = 2):
        """Очищает временные файлы старше указанного времени"""
        try:
            temp_dir = Path(TEMP_AUDIO_DIR)
            if not temp_dir.exists():
                return
            
            current_time = datetime.now().timestamp()
            cutoff_time = current_time - (older_than_hours * 3600)
            
            cleaned_count = 0
            for file_path in temp_dir.glob("voice_*"):
                if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                    try:
                        file_path.unlink()
                        cleaned_count += 1
                    except Exception as e:
                        logger.warning(f"⚠️ Не удалось удалить файл {file_path}: {e}")
            
            if cleaned_count > 0:
                logger.info(f"🧹 Очищено {cleaned_count} временных аудио файлов")
                
        except Exception as e:
            logger.error(f"❌ Ошибка при очистке временных файлов: {e}")
    
    @staticmethod
    def cleanup_file(file_path: str):
        """Удаляет конкретный файл"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.debug(f"🗑️ Удален файл: {file_path}")
        except Exception as e:
            logger.warning(f"⚠️ Не удалось удалить файл {file_path}: {e}")