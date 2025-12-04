"""
🔄 Обработчики сообщений для ignatova-stroinost-bot
"""

import logging
from typing import Dict, Any, Optional
from collections import deque
import telebot
from datetime import datetime

# Database storage
from bot.services.message_storage_service import message_storage

logger = logging.getLogger(__name__)

class MessageHandler:
    """Класс для обработки различных типов сообщений"""

    def __init__(self, bot: telebot.TeleBot, agent=None):
        self.bot = bot
        self.agent = agent
        # In-memory cache для защиты от дублирования сообщений (последние 100)
        self.processed_messages = deque(maxlen=100)
        
    async def handle_regular_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Обработка обычных сообщений"""
        user_id = message_data.get("from", {}).get("id")
        chat_id = message_data.get("chat", {}).get("id")
        text = message_data.get("text", "")
        user_name = message_data.get("from", {}).get("first_name", "Пользователь")
        message_id = message_data.get("message_id")

        if not text:
            return {"ok": True, "action": "ignored_empty_message"}

        # === ЗАЩИТА ОТ ДУБЛИРОВАНИЯ: Проверяем message_id ===
        if message_id and message_id in self.processed_messages:
            logger.warning(f"⚠️ DUPLICATE: message_id {message_id} already processed, skipping...")
            return {"ok": True, "action": "duplicate_skipped", "message_id": message_id}

        # Добавляем message_id в cache (если есть)
        if message_id:
            self.processed_messages.append(message_id)
            logger.debug(f"✅ Message ID {message_id} added to processed cache (size: {len(self.processed_messages)})")

        logger.info(f"📨 Обычное сообщение от {user_name} (ID: {user_id}): {text[:50]}...")
        
        try:
            # === СОХРАНЕНИЕ В БД: Шаг 1 - Сохранить/обновить чат ===
            try:
                chat_record = await message_storage.save_or_update_chat({
                    'id': chat_id,
                    'type': message_data.get("chat", {}).get("type", "private"),
                    'username': message_data.get("from", {}).get("username"),
                    'first_name': user_name,
                    'last_name': message_data.get("from", {}).get("last_name"),
                    'phone': message_data.get("from", {}).get("phone_number"),
                })
            except Exception as db_error:
                logger.warning(f"⚠️ MySQL недоступен, пропускаем сохранение чата: {db_error}")
                chat_record = None

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
                ai_model = getattr(self.agent, 'current_model', 'unknown')

                # Отправляем ответ
                self.bot.send_message(chat_id, response)
                logger.info(f"✅ Ответ отправлен пользователю {user_name}")

                # === СОХРАНЕНИЕ В БД: Шаг 2 - Сохранить сообщение + ответ бота ===
                if chat_record:
                    try:
                        # Проверяем, было ли это голосовое сообщение с транскрипцией
                        was_voice = message_data.get("_was_voice", False)
                        voice_transcript = message_data.get("_voice_transcript")

                        await message_storage.save_message({
                            'message_id': message_data.get("message_id", f"{user_id}_{int(datetime.utcnow().timestamp())}"),
                            'text': text if not was_voice else None,
                            'voice_transcript': voice_transcript if was_voice else None,
                            'from': message_data.get("from"),
                            'date': message_data.get("date"),
                            'is_from_user': True,
                            'is_from_business': False,
                            'bot_response': response,
                            'ai_model': ai_model,
                        }, chat=chat_record)
                        message_type = "голосовое" if was_voice else "текстовое"
                        logger.info(f"💾 Обычное {message_type} сообщение сохранено в БД для пользователя {user_name}")
                    except Exception as db_error:
                        logger.warning(f"⚠️ Не удалось сохранить сообщение в БД: {db_error}")

                return {"ok": True, "action": "message_processed"}
            else:
                # Fallback если AI недоступен
                fallback_response = self._get_fallback_response(text)
                self.bot.send_message(chat_id, fallback_response)

                # Сохраняем fallback ответ
                if chat_record:
                    try:
                        await message_storage.save_message({
                            'message_id': message_data.get("message_id", f"{user_id}_{int(datetime.utcnow().timestamp())}"),
                            'text': text,
                            'from': message_data.get("from"),
                            'date': message_data.get("date"),
                            'is_from_user': True,
                            'is_from_business': False,
                            'bot_response': fallback_response,
                            'ai_model': 'fallback',
                        }, chat=chat_record)
                    except Exception as db_error:
                        logger.warning(f"⚠️ Не удалось сохранить fallback сообщение в БД: {db_error}")

                return {"ok": True, "action": "fallback_response"}

        except Exception as e:
            logger.error(f"❌ Ошибка обработки сообщения от {user_name}: {e}")
            error_message = "Извините, произошла техническая ошибка. Попробуйте написать снова."
            self.bot.send_message(chat_id, error_message)
            return {"ok": False, "error": str(e)}
    
    async def handle_voice_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Обработка голосовых сообщений с детальной диагностикой ошибок"""
        voice = message_data.get("voice", {})
        user_id = message_data.get("from", {}).get("id")
        chat_id = message_data.get("chat", {}).get("id")
        user_name = message_data.get("from", {}).get("first_name", "Пользователь")
        duration = voice.get("duration", 0)

        logger.info(f"🎤 Голосовое сообщение от {user_name} (ID: {user_id}), длительность: {duration}с")

        try:
            # Проверяем доступность голосового сервиса
            if not hasattr(self.agent, 'voice_service') or not self.agent.voice_service:
                error_msg = "🎤 Извините, голосовые сообщения временно недоступны. Напишите текстом."
                self.bot.send_message(chat_id, error_msg)
                logger.warning(f"⚠️ Голосовой сервис недоступен для пользователя {user_name}")
                return {"ok": True, "action": "voice_unavailable"}

            # Транскрибируем голосовое сообщение
            transcription_result = await self._process_voice_transcription(voice, user_id)

            if not transcription_result.get("success"):
                error_code = transcription_result.get("error", "unknown")
                logger.error(f"❌ Ошибка транскрипции для {user_name}: {error_code}")

                # Создаём детальное сообщение об ошибке в зависимости от причины
                if error_code == "no_file_id":
                    error_msg = "🎤 Не удалось получить голосовое сообщение от Telegram. Попробуйте отправить снова."
                elif error_code == "too_long":
                    error_msg = f"🎤 Голосовое сообщение слишком длинное ({duration}с). Максимум: 10 минут (600с). Разделите на несколько частей."
                elif error_code == "too_short":
                    error_msg = "🎤 Голосовое сообщение слишком короткое. Запишите сообщение длительностью хотя бы 1 секунду."
                elif "timeout" in str(error_code).lower():
                    error_msg = "🎤 Превышено время ожидания ответа от сервиса распознавания. Попробуйте ещё раз или напишите текстом."
                elif "api" in str(error_code).lower() or "openai" in str(error_code).lower():
                    error_msg = "🎤 Сервис распознавания речи временно недоступен. Попробуйте позже или напишите текстом."
                else:
                    error_msg = f"🎤 Не удалось распознать голосовое сообщение.\n\n**Причина:** {error_code}\n\nПопробуйте ещё раз или напишите текстом."

                self.bot.send_message(chat_id, error_msg, parse_mode='Markdown')
                return {"ok": False, "error": error_code}

            text = transcription_result.get("text", "")
            if not text.strip():
                error_msg = "🎤 Голосовое сообщение не содержит распознаваемой речи. Попробуйте записать чётче или напишите текстом."
                self.bot.send_message(chat_id, error_msg)
                logger.warning(f"⚠️ Пустая транскрипция для {user_name}")
                return {"ok": True, "action": "empty_transcription"}

            logger.info(f"📝 Транскрипция от {user_name}: {text[:100]}...")

            # Обрабатываем как обычное текстовое сообщение, но сохраняем информацию о голосовом
            text_message_data = message_data.copy()
            text_message_data["text"] = text
            text_message_data["_was_voice"] = True  # Флаг что это голосовое
            text_message_data["_voice_transcript"] = text  # Транскрипция
            text_message_data["_voice_data"] = voice  # Оригинальные метаданные
            del text_message_data["voice"]  # Убираем voice данные

            return await self.handle_regular_message(text_message_data)

        except Exception as e:
            logger.error(f"❌ Необработанная ошибка голосового сообщения от {user_name}: {type(e).__name__}: {e}")
            error_msg = f"🎤 Произошла неожиданная ошибка при обработке голосового сообщения.\n\n**Тип ошибки:** {type(e).__name__}\n\nПопробуйте написать текстом."
            self.bot.send_message(chat_id, error_msg, parse_mode='Markdown')
            return {"ok": False, "error": str(e)}
    
    async def _process_voice_transcription(self, voice_data: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """Обработка транскрипции голосового сообщения с детальным логированием"""
        try:
            file_id = voice_data.get("file_id")
            duration = voice_data.get("duration", 0)

            if not file_id:
                logger.error(f"❌ Отсутствует file_id в голосовом сообщении")
                return {"success": False, "error": "no_file_id"}

            # Минимальная длительность 1 секунда
            if duration < 1:
                logger.warning(f"⚠️ Слишком короткое голосовое сообщение: {duration}с")
                return {"success": False, "error": "too_short"}

            # Максимальная длительность 10 минут
            if duration > 600:
                logger.warning(f"⚠️ Слишком длинное голосовое сообщение: {duration}с (макс: 600с)")
                return {"success": False, "error": "too_long"}

            # Получаем файл от Telegram
            logger.info(f"📥 Получаем файл {file_id} от Telegram...")
            file_info = self.bot.get_file(file_id)
            file_url = f"https://api.telegram.org/file/bot{self.bot.token}/{file_info.file_path}"
            logger.info(f"📥 URL файла получен: {file_info.file_path}")

            # Транскрибируем через голосовой сервис
            logger.info(f"🎙️ Отправляем на транскрипцию (длительность: {duration}с)...")
            transcription = await self.agent.voice_service.transcribe_audio_url(file_url)

            if not transcription or not transcription.strip():
                logger.warning(f"⚠️ Транскрипция вернула пустой текст")
                return {"success": False, "error": "empty_transcription"}

            logger.info(f"✅ Транскрипция успешна: {len(transcription)} символов")
            return {
                "success": True,
                "text": transcription,
                "duration": duration
            }

        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e)
            logger.error(f"❌ Ошибка транскрипции ({error_type}): {error_msg}")

            # Классифицируем ошибку для более понятного сообщения
            if "timeout" in error_msg.lower():
                return {"success": False, "error": "timeout"}
            elif "api" in error_msg.lower() or "openai" in error_msg.lower():
                return {"success": False, "error": "api_error"}
            else:
                return {"success": False, "error": f"{error_type}: {error_msg}"}
    
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