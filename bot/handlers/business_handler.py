"""
💼 Business API обработчик для ignatova-stroinost-bot
"""

import logging
import requests
from typing import Dict, Any, Optional
from datetime import datetime

# Database storage
from bot.services.message_storage_service import message_storage

logger = logging.getLogger(__name__)

class BusinessHandler:
    """Класс для обработки Business API сообщений"""
    
    def __init__(self, bot_token: str, agent=None):
        self.bot_token = bot_token
        self.agent = agent
        self.business_owners = {}  # {connection_id: owner_id}
        
    def handle_business_connection(self, conn_data: Dict[str, Any]) -> Dict[str, Any]:
        """Обработка Business Connection событий"""
        is_enabled = conn_data.get("is_enabled", False)
        connection_id = conn_data.get("id")
        user_info = conn_data.get("user", {})
        user_name = user_info.get("first_name", "Пользователь")
        owner_user_id = user_info.get("id")
        
        if connection_id and owner_user_id:
            if is_enabled:
                self.business_owners[connection_id] = owner_user_id
                logger.info(f"✅ Зарегистрирован владелец Business Connection: {user_name} (ID: {owner_user_id})")
            else:
                self.business_owners.pop(connection_id, None)
                logger.info(f"❌ Удален владелец Business Connection: {user_name}")
        
        status = "✅ Подключен" if is_enabled else "❌ Отключен"
        logger.info(f"{status} к Business аккаунту: {user_name}")
        logger.info(f"📊 Всего активных Business Connection: {len(self.business_owners)}")
        
        return {"ok": True, "action": "business_connection_processed"}
    
    async def handle_business_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Обработка Business сообщений с фильтрацией владельца"""
        user_id = message_data.get("from", {}).get("id")
        chat_id = message_data.get("chat", {}).get("id")
        text = message_data.get("text", "")
        user_name = message_data.get("from", {}).get("first_name", "Клиент")
        business_connection_id = message_data.get("business_connection_id")

        # Проверяем голосовое сообщение
        voice = message_data.get("voice")
        if voice:
            return await self._handle_business_voice_message(message_data)

        if not text:
            return {"ok": True, "action": "ignored_empty_business_message"}

        logger.info(f"💼 Business сообщение от {user_name} (ID: {user_id}): {text[:50]}...")

        # ФИЛЬТРАЦИЯ: Игнорируем сообщения от владельца Business аккаунта
        if self._is_owner_message(user_id, business_connection_id):
            logger.info(f"🚫 ИГНОРИРУЕМ сообщение от владельца Business аккаунта: {user_name}")
            return {"ok": True, "action": "ignored_owner_message"}

        logger.info(f"✅ ОБРАБАТЫВАЕМ сообщение от клиента: {user_name} (ID: {user_id})")

        try:
            # === СОХРАНЕНИЕ В БД: Шаг 1 - Сохранить/обновить чат ===
            chat_record = await message_storage.save_or_update_chat({
                'id': chat_id,
                'type': message_data.get("chat", {}).get("type", "private"),
                'username': message_data.get("from", {}).get("username"),
                'first_name': user_name,
                'last_name': message_data.get("from", {}).get("last_name"),
                'business_connection_id': business_connection_id,
            })

            if self.agent:
                session_id = f"business_{user_id}"

                # Создаем пользователя и сессию в Zep
                await self.agent.ensure_user_exists(str(user_id), {
                    'first_name': user_name,
                    'source': 'business_telegram'
                })
                await self.agent.ensure_session_exists(session_id, str(user_id))

                # Генерируем ответ
                response = await self.agent.generate_response(text, session_id, user_name)
                ai_model = getattr(self.agent, 'current_model', 'unknown')

                # Отправляем через Business API
                if business_connection_id:
                    result = self.send_business_message(chat_id, response, business_connection_id)
                    if result:
                        logger.info(f"✅ Business API: ответ отправлен клиенту {user_name}")

                        # === СОХРАНЕНИЕ В БД: Шаг 2 - Сохранить Business сообщение + ответ ===
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
                            'is_from_business': True,
                            'business_connection_id': business_connection_id,
                            'bot_response': response,
                            'ai_model': ai_model,
                        }, chat=chat_record)
                        logger.info(f"💾 Business сообщение сохранено в БД для клиента {user_name}")

                        return {"ok": True, "action": "business_message_sent"}
                    else:
                        logger.warning(f"⚠️ Business API не сработал, сообщение не отправлено")
                        return {"ok": False, "error": "business_api_failed"}
                else:
                    logger.error(f"❌ Отсутствует business_connection_id")
                    return {"ok": False, "error": "no_business_connection_id"}
            else:
                # Fallback если AI недоступен
                fallback_response = self._get_business_fallback_response(text)
                if business_connection_id:
                    self.send_business_message(chat_id, fallback_response, business_connection_id)

                # Сохраняем fallback ответ
                await message_storage.save_message({
                    'message_id': message_data.get("message_id", f"{user_id}_{int(datetime.utcnow().timestamp())}"),
                    'text': text,
                    'from': message_data.get("from"),
                    'date': message_data.get("date"),
                    'is_from_user': True,
                    'is_from_business': True,
                    'business_connection_id': business_connection_id,
                    'bot_response': fallback_response,
                    'ai_model': 'fallback',
                }, chat=chat_record)

                return {"ok": True, "action": "business_fallback_response"}

        except Exception as e:
            logger.error(f"❌ Ошибка обработки business сообщения от {user_name}: {e}")

            # Отправляем сообщение об ошибке через Business API
            error_message = "Извините, произошла техническая ошибка. Попробуйте написать снова."
            if business_connection_id:
                self.send_business_message(chat_id, error_message, business_connection_id)

            return {"ok": False, "error": str(e)}
    
    async def _handle_business_voice_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Обработка голосовых сообщений в Business API"""
        voice = message_data.get("voice", {})
        user_id = message_data.get("from", {}).get("id")
        chat_id = message_data.get("chat", {}).get("id")
        user_name = message_data.get("from", {}).get("first_name", "Клиент")
        business_connection_id = message_data.get("business_connection_id")
        
        logger.info(f"🎤 Business голосовое сообщение от {user_name} (ID: {user_id})")
        
        # Проверяем фильтр владельца
        if self._is_owner_message(user_id, business_connection_id):
            logger.info(f"🚫 ИГНОРИРУЕМ голосовое от владельца: {user_name}")
            return {"ok": True, "action": "ignored_owner_voice"}
        
        try:
            # Проверяем доступность голосового сервиса
            if not hasattr(self.agent, 'voice_service') or not self.agent.voice_service:
                error_msg = "🎤 Извините, голосовые сообщения временно недоступны. Напишите текстом."
                if business_connection_id:
                    self.send_business_message(chat_id, error_msg, business_connection_id)
                return {"ok": True, "action": "voice_unavailable"}
            
            # Транскрибируем
            transcription_result = await self._process_voice_transcription(voice, user_id)
            
            if not transcription_result.get("success"):
                error_msg = "🎤 Не удалось распознать голосовое сообщение. Попробуйте ещё раз или напишите текстом."
                if business_connection_id:
                    self.send_business_message(chat_id, error_msg, business_connection_id)
                return {"ok": False, "error": "transcription_failed"}
            
            text = transcription_result.get("text", "")
            if not text.strip():
                error_msg = "🎤 Голосовое сообщение пустое или не распознано. Попробуйте ещё раз."
                if business_connection_id:
                    self.send_business_message(chat_id, error_msg, business_connection_id)
                return {"ok": True, "action": "empty_transcription"}
            
            logger.info(f"📝 Business транскрипция: {text[:100]}...")

            # Обрабатываем как текстовое сообщение, но сохраняем информацию о голосовом
            text_message_data = message_data.copy()
            text_message_data["text"] = text
            text_message_data["_was_voice"] = True  # Флаг что это голосовое
            text_message_data["_voice_transcript"] = text  # Транскрипция
            text_message_data["_voice_data"] = voice  # Оригинальные метаданные
            del text_message_data["voice"]  # Убираем voice данные

            return await self.handle_business_message(text_message_data)
            
        except Exception as e:
            logger.error(f"❌ Ошибка Business голосового сообщения: {e}")
            error_msg = "🎤 Произошла ошибка при обработке голосового сообщения. Попробуйте написать текстом."
            if business_connection_id:
                self.send_business_message(chat_id, error_msg, business_connection_id)
            return {"ok": False, "error": str(e)}
    
    def _is_owner_message(self, user_id: int, business_connection_id: str) -> bool:
        """Проверяет, является ли сообщение от владельца Business аккаунта"""
        if not business_connection_id or business_connection_id not in self.business_owners:
            return False
        
        owner_id = self.business_owners[business_connection_id]
        return str(user_id) == str(owner_id)
    
    def send_business_message(self, chat_id: int, text: str, business_connection_id: str) -> Optional[Dict[str, Any]]:
        """Отправка сообщения через Business API"""
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        data = {
            "chat_id": chat_id,
            "text": text,
            "business_connection_id": business_connection_id
        }
        
        try:
            response = requests.post(url, json=data, timeout=10)
            result = response.json()
            
            if result.get("ok"):
                logger.info(f"✅ Business API: сообщение отправлено")
                return result.get("result")
            else:
                logger.error(f"❌ Business API ошибка: {result}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Business API HTTP ошибка: {e}")
            return None
    
    async def _process_voice_transcription(self, voice_data: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """Транскрипция голосового сообщения для Business API"""
        try:
            file_id = voice_data.get("file_id")
            duration = voice_data.get("duration", 0)
            
            if not file_id:
                return {"success": False, "error": "no_file_id"}
            
            if duration > 600:  # 10 минут макс
                return {"success": False, "error": "too_long"}
            
            # Получаем файл через API
            file_url = f"https://api.telegram.org/bot{self.bot_token}/getFile?file_id={file_id}"
            file_response = requests.get(file_url, timeout=10)
            file_info = file_response.json()
            
            if not file_info.get("ok"):
                return {"success": False, "error": "file_not_found"}
            
            file_path = file_info["result"]["file_path"]
            audio_url = f"https://api.telegram.org/file/bot{self.bot_token}/{file_path}"
            
            # Транскрибируем
            transcription = await self.agent.voice_service.transcribe_audio_url(audio_url)
            
            return {
                "success": True,
                "text": transcription,
                "duration": duration
            }
            
        except Exception as e:
            logger.error(f"❌ Business транскрипция ошибка: {e}")
            return {"success": False, "error": str(e)}
    
    def _get_business_fallback_response(self, text: str) -> str:
        """Простые ответы для Business API когда AI недоступен"""
        text_lower = text.lower()
        
        if any(word in text_lower for word in ['привет', 'hello', 'hi', 'здравствуй']):
            return "👋 Здравствуйте! Меня зовут Анастасия, я консультант ignatova-stroinost. Чем могу помочь с производством одежды?"
            
        elif any(word in text_lower for word in ['цена', 'стоимость', 'сколько']):
            return "💰 Стоимость зависит от объема заказа и типа изделий. Расскажите подробнее о ваших потребностях, и я подготовлю персональное предложение."
            
        elif any(word in text_lower for word in ['спасибо', 'thanks']):
            return "😊 Всегда пожалуйста! Рада была помочь!"
            
        else:
            return "Получила ваш запрос! Сейчас подготовлю детальный ответ по вашему вопросу. Минуточку!\n\nС уважением,\nАнастасия\nignatova-stroinost"
    
    def get_status(self) -> Dict[str, Any]:
        """Получить статус Business Handler"""
        return {
            "total_connections": len(self.business_owners),
            "business_owners": self.business_owners,
            "filter_active": len(self.business_owners) > 0,
            "current_time": datetime.now().isoformat()
        }