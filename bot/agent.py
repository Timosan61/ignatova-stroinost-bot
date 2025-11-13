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

# Опциональный импорт голосового сервиса
try:
    from .voice.voice_service import VoiceService
    VOICE_SERVICE_AVAILABLE = True
except ImportError as e:
    VoiceService = None
    VOICE_SERVICE_AVAILABLE = False
    print(f"⚠️ VoiceService недоступен: {e}")

# Настройка логирования
logger = logging.getLogger(__name__)


class TextilProAgent:
    def __init__(self):
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
        
        # Инициализируем голосовой сервис
        if VOICE_ENABLED and OPENAI_API_KEY and TELEGRAM_BOT_TOKEN and VOICE_SERVICE_AVAILABLE:
            try:
                self.voice_service = VoiceService(TELEGRAM_BOT_TOKEN, OPENAI_API_KEY)
                print("✅ Голосовой сервис инициализирован")
            except Exception as e:
                print(f"❌ Ошибка инициализации голосового сервиса: {e}")
                self.voice_service = None
        else:
            self.voice_service = None
            if not VOICE_ENABLED:
                print("⚠️ Голосовые сообщения отключены в конфигурации")
            elif not VOICE_SERVICE_AVAILABLE:
                print("⚠️ VoiceService не доступен - голосовые сообщения недоступны")
            elif not OPENAI_API_KEY:
                print("⚠️ OPENAI_API_KEY отсутствует - голосовые сообщения недоступны")
            elif not TELEGRAM_BOT_TOKEN:
                print("⚠️ TELEGRAM_BOT_TOKEN отсутствует - голосовые сообщения недоступны")
        
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
    
    async def search_knowledge_base(self, query: str, limit: int = 5) -> str:
        """Поиск релевантной информации в базе знаний через Zep Knowledge Graph"""
        if not self.zep_client:
            logger.info("⚠️ Zep недоступен, пропускаем поиск в базе знаний")
            return ""
        
        try:
            logger.info(f"🔍 Ищем в базе знаний: '{query[:50]}...'")
            
            # Ищем по всем категориям знаний в Memory
            results = []
            
            categories = [
                'training_summary', 'training_faq', 'scripts', 'objections', 
                'faq', 'techniques', 'sales_methodology', 'general'
            ]
            
            for category in categories:
                # Ищем во всех подсессиях этой категории
                for session_part in range(1, 15):  # Максимум 15 подсессий на категорию
                    try:
                        session_id = f"knowledge_{category}_session_{session_part}"
                        
                        # Получаем всю память сессии (так как search deprecated)
                        memory = await self.zep_client.memory.get(session_id=session_id)
                        
                        if memory and memory.messages:
                            # Локально фильтруем сообщения по запросу
                            query_lower = query.lower()
                            found_messages = []
                            
                            for msg in memory.messages:
                                if msg.role_type == 'assistant' and msg.content:
                                    # Проверяем содержит ли сообщение запрос
                                    content_lower = msg.content.lower()
                                    if any(word in content_lower for word in query_lower.split()):
                                        # Добавляем результат с метаданными источника
                                        result_with_source = {
                                            'content': msg.content,
                                            'category': category,
                                            'session': session_part
                                        }
                                        found_messages.append(result_with_source)
                                        if len(found_messages) >= 2:  # Максимум 2 результата с сессии
                                            break
                            
                            results.extend(found_messages)
                            
                            # Ограничиваем общее количество результатов
                            if len(results) >= limit:
                                break
                                    
                        if len(results) >= limit:
                            break
                            
                    except Exception as e:
                        # Если сессии не существует, прерываем поиск по этой категории
                        if "404" in str(e):
                            break
                        continue
                
                if len(results) >= limit:
                    break
            
            if not results:
                logger.info("📭 В базе знаний ничего не найдено")
                return "", []
            
            # Формируем контекст из найденных результатов
            context_parts = []
            sources_used = []  # Список использованных источников
            
            for i, result in enumerate(results):
                try:
                    # Извлекаем содержимое и метаданные из результата поиска
                    if isinstance(result, dict) and 'content' in result:
                        content = result['content']
                        category = result.get('category', 'unknown').upper()
                        session = result.get('session', '?')
                        source_info = f"{category}-сессия{session}"
                    elif hasattr(result, 'content'):
                        content = result.content
                        source_info = f"UNKNOWN-источник{i+1}"
                    elif hasattr(result, 'data'):
                        content = result.data
                        source_info = f"UNKNOWN-источник{i+1}"
                    else:
                        content = str(result)
                        source_info = f"UNKNOWN-источник{i+1}"
                    
                    # Ограничиваем длину каждого результата
                    if len(content) > 800:
                        content = content[:800] + "..."
                    
                    context_parts.append(f"[{source_info}] {content}")
                    sources_used.append(source_info)
                    
                except Exception as e:
                    logger.warning(f"⚠️ Ошибка обработки результата {i+1}: {e}")
                    continue
            
            context = "\n\n".join(context_parts)
            
            # Ограничиваем общий размер контекста
            max_context_chars = 3000
            if len(context) > max_context_chars:
                context = context[:max_context_chars] + "\n\n[...контекст обрезан...]"
            
            logger.info(f"✅ Найдено {len(results)} релевантных фрагментов ({len(context)} символов)")
            # Возвращаем кортеж (контекст, список источников)
            return context, sources_used
            
        except Exception as e:
            logger.error(f"❌ Ошибка поиска в базе знаний: {e}")
            print(f"❌ Ошибка поиска в базе знаний: {e}")
            return "", []
    
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
    
    async def call_llm(self, messages: list, max_tokens: int = 1000, temperature: float = 0.5) -> str:
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

            # Ищем релевантную информацию в базе знаний
            knowledge_context, sources_used = await self.search_knowledge_base(user_message, limit=3)

            # Пытаемся получить контекст из Zep Memory
            zep_context = await self.get_zep_memory_context(session_id)
            zep_history = await self.get_zep_recent_messages(session_id)

            # Добавляем контекст из базы знаний
            if knowledge_context:
                system_prompt += f"\n\n=== РЕЛЕВАНТНАЯ ИНФОРМАЦИЯ ИЗ БАЗЫ ЗНАНИЙ ===\n{knowledge_context}\n=== КОНЕЦ БАЗЫ ЗНАНИЙ ==="

            # Добавляем контекст и историю в системный промпт
            if zep_context:
                system_prompt += f"\n\nКонтекст предыдущих разговоров:\n{zep_context}"

            if zep_history:
                system_prompt += f"\n\nПоследние сообщения:\n{zep_history}"


            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]

            # Используем LLM роутер
            if self.openai_client or self.anthropic_client:
                try:
                    logger.info(f"🤖 Генерируем ответ для: '{user_message[:50]}...'")
                    logger.info(f"📊 Найдено источников в базе знаний: {len(sources_used)}")
                    bot_response = await self.call_llm(messages, max_tokens=2000, temperature=0.5)

                    # Добавляем источники в конец ответа если есть
                    if sources_used and bot_response:
                        sources_text = ", ".join(sources_used)
                        bot_response += f"\n\n📚 **Источник:** {sources_text}"

                    logger.info(f"✅ Ответ сгенерирован успешно (длина: {len(bot_response)} символов)")

                except Exception as llm_error:
                    logger.error(f"❌ Ошибка LLM: {type(llm_error).__name__}: {llm_error}")
                    logger.error(f"❌ Детали: {str(llm_error)}")
                    print(f"❌ КРИТИЧЕСКАЯ ОШИБКА LLM: {llm_error}")

                    # Улучшенный fallback - используем найденную информацию
                    if knowledge_context:
                        bot_response = f"⚠️ AI временно недоступен, но нашла информацию в базе знаний:\n\n{knowledge_context[:500]}"
                        if sources_used:
                            sources_text = ", ".join(sources_used)
                            bot_response += f"\n\n📚 **Источник:** {sources_text}"
                        bot_response += "\n\n🔄 Попробуйте задать вопрос еще раз или уточните запрос.\n\nКристина, ignatova-stroinost"
                    else:
                        # Простые ответы как последний fallback
                        user_message_lower = user_message.lower()

                        if any(word in user_message_lower for word in ['привет', 'hello', 'hi', 'здравствуй']):
                            bot_response = "👋 Привет! Меня зовут Кристина, я ассистент для менеджеров по продажам. Помогаю с:\n• Подбором скриптов для клиентов\n• Обработкой возражений\n• Планированием follow-up'ов\n\nО чём хотите посоветоваться?"
                        elif any(word in user_message_lower for word in ['цена', 'стоимость', 'сколько']):
                            bot_response = "💰 У нас есть несколько продуктов:\n• Диагностика психотипа (бесплатно)\n• Марафон похудения (990₽)\n• 4 практики (990₽)\n• Полный курс\n\nЧто вас интересует?"
                        else:
                            bot_response = f"⚠️ AI временно недоступен. Попробуйте:\n• Переформулировать вопрос\n• Задать конкретный вопрос (например: 'как обработать возражение о цене?')\n• Написать позже\n\nКристина, ignatova-stroinost"
            else:
                # Простая логика ответов если нет API ключей
                user_message_lower = user_message.lower()

                if any(word in user_message_lower for word in ['привет', 'hello', 'hi', 'здравствуй']):
                    bot_response = "👋 Привет! Меня зовут Кристина, я ассистент для менеджеров по продажам. Помогаю с:\n• Подбором скриптов для клиентов\n• Обработкой возражений\n• Планированием follow-up'ов\n\nО чём хотите посоветоваться?"
                elif any(word in user_message_lower for word in ['цена', 'стоимость', 'сколько']):
                    bot_response = "💰 У нас есть несколько продуктов:\n• Диагностика психотипа (бесплатно)\n• Марафон похудения (990₽)\n• 4 практики (990₽)\n• Полный курс\n\nЧто вас интересует?"
                else:
                    bot_response = f"⚠️ AI сервис не настроен. Обратитесь к администратору для настройки OpenAI или Anthropic API.\n\nКристина, ignatova-stroinost"

            # Сохраняем в Zep Memory (с fallback на локальное хранилище)
            await self.add_to_zep_memory(session_id, user_message, bot_response, user_name)

            return bot_response

        except Exception as e:
            logger.error(f"❌ Критическая ошибка при генерации ответа: {e}")
            print(f"❌ Критическая ошибка: {e}")
            import traceback
            traceback.print_exc()
            return "Извините, произошла техническая ошибка. Попробуйте написать снова или обратитесь к администратору.\n\nКристина, ignatova-stroinost"
    
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
    

    def get_instruction_info(self) -> dict:
        """Получает информацию о текущих инструкциях для админ-панели"""
        return {
            "last_updated": self.instruction.get("last_updated", "неизвестно"),
            "system_instruction_length": len(self.instruction.get("system_instruction", "")),
            "welcome_message": self.instruction.get("welcome_message", ""),
            "openai_enabled": self.openai_client is not None,
            "anthropic_enabled": self.anthropic_client is not None,
            "llm_available": self.openai_client is not None or self.anthropic_client is not None,
            "zep_enabled": self.zep_client is not None
        }


agent = TextilProAgent()