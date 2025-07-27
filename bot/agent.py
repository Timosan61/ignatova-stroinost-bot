import json
import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Any

import openai
import anthropic
from zep_cloud.client import AsyncZep
from zep_cloud.types import Message

from .config import (
    INSTRUCTION_FILE, OPENAI_API_KEY, ANTHROPIC_API_KEY, OPENAI_MODEL, 
    ANTHROPIC_MODEL, ZEP_API_KEY, VOICE_ENABLED, TELEGRAM_BOT_TOKEN
)

# Настройка логирования
logger = logging.getLogger(__name__)


class TextilProAgent:
    def __init__(self):
        # Инициализируем голосовой сервис если доступен
        self.voice_service = None
        if VOICE_ENABLED and TELEGRAM_BOT_TOKEN:
            try:
                from .voice import VoiceService
                self.voice_service = VoiceService(TELEGRAM_BOT_TOKEN, OPENAI_API_KEY)
                print("✅ Голосовой сервис инициализирован")
            except Exception as e:
                print(f"❌ Ошибка инициализации голосового сервиса: {e}")
                self.voice_service = None
        else:
            if not VOICE_ENABLED:
                print("⚠️ Голосовой сервис отключен (OPENAI_API_KEY не найден)")
            if not TELEGRAM_BOT_TOKEN:
                print("⚠️ Голосовой сервис отключен (TELEGRAM_BOT_TOKEN не найден)")
        # Инициализируем OpenAI клиент если API ключ доступен
        if OPENAI_API_KEY:
            try:
                self.openai_client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)
                print("✅ OpenAI клиент инициализирован")
            except Exception as e:
                print(f"❌ Ошибка инициализации OpenAI: {e}")
                self.openai_client = None
        else:
            self.openai_client = None
            print("⚠️ OpenAI API ключ не найден")
            
        # Инициализируем Anthropic клиент если API ключ доступен
        if ANTHROPIC_API_KEY:
            try:
                self.anthropic_client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
                print("✅ Anthropic клиент инициализирован")
            except Exception as e:
                print(f"❌ Ошибка инициализации Anthropic: {e}")
                self.anthropic_client = None
        else:
            self.anthropic_client = None
            print("⚠️ Anthropic API ключ не найден")
            
        # Проверяем что хотя бы один LLM доступен
        if not self.openai_client and not self.anthropic_client:
            print("⚠️ Ни один LLM не доступен, используется упрощенный режим")
        
        # Инициализируем Zep клиент если API ключ доступен
        if ZEP_API_KEY and ZEP_API_KEY != "test_key":
            try:
                self.zep_client = AsyncZep(api_key=ZEP_API_KEY)
                print(f"✅ Zep клиент инициализирован с ключом длиной {len(ZEP_API_KEY)} символов")
                print(f"🔑 Zep API Key начинается с: {ZEP_API_KEY[:8]}...")
            except Exception as e:
                print(f"❌ Ошибка инициализации Zep клиента: {e}")
                self.zep_client = None
        else:
            self.zep_client = None
            if not ZEP_API_KEY:
                print("⚠️ ZEP_API_KEY не установлен, используется локальная память")
            else:
                print(f"⚠️ ZEP_API_KEY имеет значение 'test_key', используется локальная память")
        self.instruction = self._load_instruction()
        self.user_sessions = {}  # Резервное хранение сессий в памяти
    
    def _load_instruction(self) -> Dict[str, Any]:
        try:
            with open(INSTRUCTION_FILE, 'r', encoding='utf-8') as f:
                instruction = json.load(f)
                logger.info(f"✅ Инструкции успешно загружены из {INSTRUCTION_FILE}")
                logger.info(f"📝 Последнее обновление: {instruction.get('last_updated', 'неизвестно')}")
                logger.info(f"📏 Длина системной инструкции: {len(instruction.get('system_instruction', ''))}")
                print(f"✅ Инструкции успешно загружены из {INSTRUCTION_FILE}")
                print(f"📝 Последнее обновление: {instruction.get('last_updated', 'неизвестно')}")
                return instruction
        except FileNotFoundError:
            logger.warning(f"⚠️ ВНИМАНИЕ: Файл {INSTRUCTION_FILE} не найден! Используется базовая инструкция.")
            print(f"⚠️ ВНИМАНИЕ: Файл {INSTRUCTION_FILE} не найден! Используется базовая инструкция.")
            return {
                "system_instruction": "Вы - помощник службы поддержки Textil PRO.",
                "welcome_message": "Добро пожаловать! Чем могу помочь?",
                "last_updated": datetime.now().isoformat()
            }
        except Exception as e:
            print(f"❌ Ошибка при загрузке инструкций: {e}")
            return {
                "system_instruction": "Вы - помощник службы поддержки Textil PRO.",
                "welcome_message": "Добро пожаловать! Чем могу помочь?",
                "last_updated": datetime.now().isoformat()
            }
    
    def reload_instruction(self):
        logger.info("🔄 Перезагрузка инструкций...")
        print("🔄 Перезагрузка инструкций...")
        old_updated = self.instruction.get('last_updated', 'неизвестно')
        self.instruction = self._load_instruction()
        new_updated = self.instruction.get('last_updated', 'неизвестно')
        
        if old_updated != new_updated:
            logger.info(f"✅ Инструкции обновлены: {old_updated} -> {new_updated}")
            print(f"✅ Инструкции обновлены: {old_updated} -> {new_updated}")
        else:
            logger.info("📝 Инструкции перезагружены (без изменений)")
            print("📝 Инструкции перезагружены (без изменений)")
    
    async def add_to_zep_memory(self, session_id: str, user_message: str, bot_response: str, user_name: str = None):
        """Добавляет сообщения в Zep Memory с именами пользователей"""
        if not self.zep_client:
            print(f"⚠️ Zep клиент не инициализирован, используем локальную память для {session_id}")
            self.add_to_local_session(session_id, user_message, bot_response)
            return False
            
        try:
            # Используем имя пользователя или ID для роли
            user_role = user_name if user_name else f"User_{session_id.split('_')[-1][:6]}"
            
            messages = [
                Message(
                    role=user_role,  # Имя пользователя вместо generic "user"
                    role_type="user",
                    content=user_message
                ),
                Message(
                    role="Анастасия",  # Имя бота-консультанта
                    role_type="assistant",
                    content=bot_response
                )
            ]
            
            await self.zep_client.memory.add(session_id=session_id, messages=messages)
            print(f"✅ Сообщения добавлены в Zep Cloud для сессии {session_id}")
            print(f"   📝 User: {user_message[:50]}...")
            print(f"   🤖 Bot: {bot_response[:50]}...")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка при добавлении в Zep: {type(e).__name__}: {e}")
            # Fallback: добавляем в локальную память
            self.add_to_local_session(session_id, user_message, bot_response)
            return False
    
    async def get_zep_memory_context(self, session_id: str) -> str:
        """Получает контекст из Zep Memory"""
        if not self.zep_client:
            print(f"⚠️ Zep не доступен, используем локальную историю для {session_id}")
            return self.get_local_session_history(session_id)
            
        try:
            memory = await self.zep_client.memory.get(session_id=session_id)
            context = memory.context if memory.context else ""
            print(f"✅ Получен контекст из Zep для сессии {session_id}, длина: {len(context)}")
            return context
            
        except Exception as e:
            print(f"❌ Ошибка при получении контекста из Zep: {type(e).__name__}: {e}")
            return self.get_local_session_history(session_id)
    
    async def get_zep_recent_messages(self, session_id: str, limit: int = 6) -> str:
        """Получает последние сообщения из Zep Memory"""
        try:
            memory = await self.zep_client.memory.get(session_id=session_id)
            if not memory.messages:
                return ""
            
            recent_messages = memory.messages[-limit:]
            formatted_messages = []
            
            for msg in recent_messages:
                role = "Пользователь" if msg.role_type == "user" else "Ассистент"
                formatted_messages.append(f"{role}: {msg.content}")
            
            return "\n".join(formatted_messages)
            
        except Exception as e:
            print(f"❌ Ошибка при получении сообщений из Zep: {e}")
            return self.get_local_session_history(session_id)
    
    def add_to_local_session(self, session_id: str, user_message: str, bot_response: str):
        """Резервное локальное хранение сессий"""
        if session_id not in self.user_sessions:
            self.user_sessions[session_id] = []
        
        self.user_sessions[session_id].append({
            "user": user_message,
            "assistant": bot_response,
            "timestamp": datetime.now().isoformat()
        })
        
        # Ограничиваем историю 10 последними сообщениями
        if len(self.user_sessions[session_id]) > 10:
            self.user_sessions[session_id] = self.user_sessions[session_id][-10:]
    
    def get_local_session_history(self, session_id: str) -> str:
        """Получает историю из локального хранилища"""
        if session_id not in self.user_sessions:
            return ""
        
        history = []
        for exchange in self.user_sessions[session_id][-6:]:  # Последние 6 обменов
            history.append(f"Пользователь: {exchange['user']}")
            history.append(f"Ассистент: {exchange['assistant']}")
        
        return "\n".join(history) if history else ""
    
    async def call_llm(self, messages: list, max_tokens: int = 1000, temperature: float = 0.7) -> str:
        """Роутер LLM запросов с fallback между OpenAI и Anthropic"""
        
        # Сначала пробуем OpenAI
        if self.openai_client:
            try:
                logger.info("🤖 Пытаемся использовать OpenAI")
                response = await self.openai_client.chat.completions.create(
                    model=OPENAI_MODEL,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature
                )
                result = response.choices[0].message.content
                logger.info("✅ OpenAI ответ получен")
                return result
                
            except Exception as e:
                logger.error(f"❌ Ошибка OpenAI: {e}")
                print(f"❌ OpenAI недоступен: {e}")
        
        # Fallback на Anthropic
        if self.anthropic_client:
            try:
                logger.info("🤖 Fallback на Anthropic Claude")
                
                # Конвертируем сообщения для Anthropic API
                system_message = ""
                user_messages = []
                
                for msg in messages:
                    if msg["role"] == "system":
                        system_message = msg["content"]
                    else:
                        user_messages.append(msg)
                
                response = await self.anthropic_client.messages.create(
                    model=ANTHROPIC_MODEL,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=system_message,
                    messages=user_messages
                )
                
                result = response.content[0].text
                logger.info("✅ Anthropic ответ получен")
                return result
                
            except Exception as e:
                logger.error(f"❌ Ошибка Anthropic: {e}")
                print(f"❌ Anthropic недоступен: {e}")
        
        # Если оба LLM недоступны
        logger.error("❌ Все LLM недоступны")
        raise Exception("Все LLM провайдеры недоступны")
    
    async def generate_response(self, user_message: str, session_id: str, user_name: str = None) -> str:
        try:
            system_prompt = self.instruction.get("system_instruction", "")
            
            # Пытаемся получить контекст из Zep Memory
            zep_context = await self.get_zep_memory_context(session_id)
            zep_history = await self.get_zep_recent_messages(session_id)
            
            # Добавляем контекст и историю в системный промпт
            if zep_context:
                system_prompt += f"\n\nКонтекст предыдущих разговоров:\n{zep_context}"
            
            if zep_history:
                system_prompt += f"\n\nПоследние сообщения:\n{zep_history}"
            
            # Дополнительное напоминание о форматировании и приветствии
            system_prompt += "\n\n⚠️ КРИТИЧЕСКИ ВАЖНО: Форматируй ответы с абзацами! Используй двойные переносы строк между смысловыми блоками. НЕ пиши сплошным текстом!"
            system_prompt += "\n\n⚠️ ПРАВИЛО ПРИВЕТСТВИЯ: НЕ начинай каждый ответ с 'Здравствуйте!' Приветствуй только при первом сообщении или /start. В продолжении диалога сразу переходи к сути!"
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]
            
            # Используем LLM роутер
            if self.openai_client or self.anthropic_client:
                try:
                    bot_response = await self.call_llm(messages, max_tokens=1000, temperature=0.7)
                except Exception as llm_error:
                    logger.error(f"❌ Все LLM недоступны: {llm_error}")
                    # Fallback на простые ответы если все LLM недоступны
                    user_message_lower = user_message.lower()
                    
                    if any(word in user_message_lower for word in ['привет', 'hello', 'hi', 'здравствуй']):
                        bot_response = "👋 Привет! Меня зовут Кристина, я консультант ignatova-stroinost. Чем могу помочь?"
                    elif any(word in user_message_lower for word in ['цена', 'стоимость', 'сколько']):
                        bot_response = "💰 Цены зависят от объема и типа услуг. Расскажите подробнее о ваших потребностях."
                    else:
                        bot_response = f"Поняла ваш вопрос! Подготовлю детальный ответ специально для вас. Минуточку!\n\nКристина, ignatova-stroinost"
            else:
                # Простая логика ответов если нет API ключей
                user_message_lower = user_message.lower()
                
                if any(word in user_message_lower for word in ['привет', 'hello', 'hi', 'здравствуй']):
                    bot_response = "👋 Привет! Меня зовут Кристина, я консультант ignatova-stroinost. Чем могу помочь?"
                elif any(word in user_message_lower for word in ['цена', 'стоимость', 'сколько']):
                    bot_response = "💰 Цены зависят от объема и типа услуг. Расскажите подробнее о ваших потребностях."
                else:
                    bot_response = f"Поняла ваш вопрос! Подготовлю детальный ответ специально для вас. Минуточку!\n\nКристина, ignatova-stroinost"
            
            # Сохраняем в Zep Memory (с fallback на локальное хранилище)
            await self.add_to_zep_memory(session_id, user_message, bot_response, user_name)
            
            return bot_response
            
        except Exception as e:
            print(f"Ошибка при генерации ответа: {e}")
            return "Извините, произошла техническая ошибка. Попробуйте написать снова или обратитесь ко мне напрямую.\n\nАнастасия, Textil PRO"
    
    async def ensure_user_exists(self, user_id: str, user_data: Dict[str, Any] = None):
        """Создает пользователя в Zep если его еще нет"""
        if not self.zep_client:
            return False
            
        try:
            # Пытаемся получить пользователя
            try:
                user = await self.zep_client.user.get(user_id=user_id)
                print(f"✅ Пользователь {user_id} уже существует в Zep")
                return True
            except:
                # Пользователь не существует, создаем
                pass
            
            # Создаем нового пользователя
            user_info = user_data or {}
            await self.zep_client.user.add(
                user_id=user_id,
                first_name=user_info.get('first_name', 'User'),
                last_name=user_info.get('last_name', ''),
                email=user_info.get('email', f'{user_id}@telegram.user'),
                metadata={
                    'source': 'telegram',
                    'created_at': datetime.now().isoformat()
                }
            )
            print(f"✅ Создан новый пользователь в Zep: {user_id}")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка при создании пользователя в Zep: {e}")
            return False
    
    async def ensure_session_exists(self, session_id: str, user_id: str):
        """Создает сессию в Zep если ее еще нет"""
        if not self.zep_client:
            return False
            
        try:
            # Создаем сессию
            await self.zep_client.memory.add_session(
                session_id=session_id,
                user_id=user_id,
                metadata={
                    'channel': 'telegram',
                    'created_at': datetime.now().isoformat()
                }
            )
            print(f"✅ Создана сессия в Zep: {session_id} для пользователя {user_id}")
            return True
            
        except Exception as e:
            # Сессия может уже существовать или будет создана автоматически
            print(f"ℹ️ Сессия {session_id} возможно уже существует или будет создана автоматически")
            return True
    
    def get_welcome_message(self) -> str:
        return self.instruction.get("welcome_message", "Добро пожаловать!")
    
    async def process_voice_message(
        self, 
        voice_data: Dict[str, Any], 
        user_id: str, 
        message_id: str,
        user_name: str = None
    ) -> Dict[str, Any]:
        """
        Обрабатывает голосовое сообщение: транскрибирует и генерирует ответ
        
        Args:
            voice_data: Данные голосового сообщения от Telegram
            user_id: ID пользователя  
            message_id: ID сообщения
            user_name: Имя пользователя
            
        Returns:
            Dict с результатом обработки
        """
        if not self.voice_service:
            return {
                "success": False,
                "error": "Голосовые сообщения не поддерживаются",
                "transcribed_text": None,
                "ai_response": None
            }
        
        try:
            # Этап 1: Транскрибируем голосовое сообщение
            logger.info(f"🎤 Начинаем обработку голосового сообщения от {user_name or user_id}")
            
            voice_result = await self.voice_service.process_voice_message(
                voice_data, user_id, message_id, language="ru"
            )
            
            if not voice_result["success"]:
                logger.error(f"❌ Ошибка транскрипции: {voice_result['error']}")
                return {
                    "success": False,
                    "error": f"Ошибка обработки голосового сообщения: {voice_result['error']}",
                    "transcribed_text": None,
                    "ai_response": None
                }
            
            transcribed_text = voice_result["text"]
            logger.info(f"✅ Транскрипция завершена: {transcribed_text[:50]}...")
            
            # Этап 2: Генерируем ответ через AI агента
            session_id = f"user_{user_id}"
            
            # Создаем пользователя в Zep если нужно
            if self.zep_client:
                await self.ensure_user_exists(f"user_{user_id}", {
                    'first_name': user_name or f"User_{user_id}",
                    'email': f'{user_id}@telegram.user'
                })
                await self.ensure_session_exists(session_id, f"user_{user_id}")
            
            # Генерируем ответ на транскрибированный текст
            ai_response = await self.generate_response(
                f"[Голосовое сообщение]: {transcribed_text}", 
                session_id, 
                user_name
            )
            
            logger.info(f"✅ AI ответ сгенерирован: {ai_response[:50]}...")
            
            return {
                "success": True,
                "transcribed_text": transcribed_text,
                "ai_response": ai_response,
                "processing_time": voice_result.get("processing_time", 0),
                "duration": voice_result.get("duration", 0),
                "char_count": voice_result.get("char_count", 0)
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки голосового сообщения: {e}")
            logger.error(f"📋 Данные voice_data: {voice_data}")
            logger.error(f"🔍 Тип ошибки: {type(e).__name__}")
            import traceback
            logger.error(f"📄 Полный трейс: {traceback.format_exc()}")
            return {
                "success": False,
                "error": f"Неожиданная ошибка: {str(e)}",
                "transcribed_text": None,
                "ai_response": None
            }

    def get_instruction_info(self) -> dict:
        """Получает информацию о текущих инструкциях для админ-панели"""
        return {
            "last_updated": self.instruction.get("last_updated", "неизвестно"),
            "system_instruction_length": len(self.instruction.get("system_instruction", "")),
            "welcome_message": self.instruction.get("welcome_message", ""),
            "openai_enabled": self.openai_client is not None,
            "anthropic_enabled": self.anthropic_client is not None,
            "llm_available": self.openai_client is not None or self.anthropic_client is not None,
            "zep_enabled": self.zep_client is not None,
            "voice_enabled": self.voice_service is not None
        }


agent = TextilProAgent()