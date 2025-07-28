"""
🔄 Обработчики сообщений для ignatova-stroinost-bot
"""

import logging
from typing import Dict, Any, Optional
import telebot
from datetime import datetime

logger = logging.getLogger(__name__)

class MessageHandler:
    """Класс для обработки различных типов сообщений"""
    
    def __init__(self, bot: telebot.TeleBot, agent=None):
        self.bot = bot
        self.agent = agent
        
    async def handle_regular_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Обработка обычных сообщений"""
        user_id = message_data.get("from", {}).get("id")
        chat_id = message_data.get("chat", {}).get("id")
        text = message_data.get("text", "")
        user_name = message_data.get("from", {}).get("first_name", "Пользователь")
        
        if not text:
            return {"ok": True, "action": "ignored_empty_message"}
            
        logger.info(f"📨 Обычное сообщение от {user_name} (ID: {user_id}): {text[:50]}...")
        
        try:
            if self.agent:
                session_id = f"user_{user_id}"
                # Убедимся что пользователь и сессия существуют в Zep
                await self.agent.ensure_user_exists(str(user_id), {
                    'first_name': user_name,
                    'source': 'telegram'
                })
                await self.agent.ensure_session_exists(session_id, str(user_id))
                
                # Генерируем ответ
                response = await self.agent.generate_response(text, session_id, user_name)
                
                # Отправляем ответ
                self.bot.send_message(chat_id, response)
                logger.info(f"✅ Ответ отправлен пользователю {user_name}")
                
                return {"ok": True, "action": "message_processed"}
            else:
                # Fallback если AI недоступен
                fallback_response = self._get_fallback_response(text)
                self.bot.send_message(chat_id, fallback_response)
                return {"ok": True, "action": "fallback_response"}
                
        except Exception as e:
            logger.error(f"❌ Ошибка обработки сообщения от {user_name}: {e}")
            error_message = "Извините, произошла техническая ошибка. Попробуйте написать снова."
            self.bot.send_message(chat_id, error_message)
            return {"ok": False, "error": str(e)}
    
    async def handle_voice_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Обработка голосовых сообщений"""
        voice = message_data.get("voice", {})
        user_id = message_data.get("from", {}).get("id")
        chat_id = message_data.get("chat", {}).get("id")
        user_name = message_data.get("from", {}).get("first_name", "Пользователь")
        
        logger.info(f"🎤 Голосовое сообщение от {user_name} (ID: {user_id})")
        
        try:
            # Проверяем доступность голосового сервиса
            if not hasattr(self.agent, 'voice_service') or not self.agent.voice_service:
                error_msg = "🎤 Извините, голосовые сообщения временно недоступны. Напишите текстом."
                self.bot.send_message(chat_id, error_msg)
                return {"ok": True, "action": "voice_unavailable"}
            
            # Транскрибируем голосовое сообщение
            transcription_result = await self._process_voice_transcription(voice, user_id)
            
            if not transcription_result.get("success"):
                error_msg = "🎤 Не удалось распознать голосовое сообщение. Попробуйте ещё раз или напишите текстом."
                self.bot.send_message(chat_id, error_msg)
                return {"ok": False, "error": "transcription_failed"}
            
            text = transcription_result.get("text", "")
            if not text.strip():
                error_msg = "🎤 Голосовое сообщение пустое или не распознано. Попробуйте ещё раз."
                self.bot.send_message(chat_id, error_msg)
                return {"ok": True, "action": "empty_transcription"}
            
            logger.info(f"📝 Транскрипция: {text[:100]}...")
            
            # Обрабатываем как обычное текстовое сообщение
            text_message_data = message_data.copy()
            text_message_data["text"] = text
            
            return await self.handle_regular_message(text_message_data)
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки голосового сообщения: {e}")
            error_msg = "🎤 Произошла ошибка при обработке голосового сообщения. Попробуйте написать текстом."
            self.bot.send_message(chat_id, error_msg)
            return {"ok": False, "error": str(e)}
    
    async def _process_voice_transcription(self, voice_data: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """Обработка транскрипции голосового сообщения"""
        try:
            file_id = voice_data.get("file_id")
            duration = voice_data.get("duration", 0)
            
            if not file_id:
                return {"success": False, "error": "no_file_id"}
            
            # Максимальная длительность 10 минут
            if duration > 600:
                return {"success": False, "error": "too_long"}
            
            # Получаем файл от Telegram
            file_info = self.bot.get_file(file_id)
            file_url = f"https://api.telegram.org/file/bot{self.bot.token}/{file_info.file_path}"
            
            # Транскрибируем через голосовой сервис
            transcription = await self.agent.voice_service.transcribe_audio_url(file_url)
            
            return {
                "success": True,
                "text": transcription,
                "duration": duration
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка транскрипции: {e}")
            return {"success": False, "error": str(e)}
    
    def _get_fallback_response(self, text: str) -> str:
        """Простые ответы когда AI недоступен"""
        text_lower = text.lower()
        
        if any(word in text_lower for word in ['привет', 'hello', 'hi', 'здравствуй']):
            return "👋 Привет! Меня зовут Анастасия, я консультант ignatova-stroinost. Чем могу помочь?"
            
        elif any(word in text_lower for word in ['цена', 'стоимость', 'сколько']):
            return "💰 Цены зависят от объема и типа услуг. Расскажите подробнее о ваших потребностях."
            
        elif any(word in text_lower for word in ['спасибо', 'thanks']):
            return "😊 Пожалуйста! Всегда рада помочь!"
            
        else:
            return "Получила ваше сообщение! Подготовлю детальный ответ. Минуточку!\n\nАнастасия, ignatova-stroinost"