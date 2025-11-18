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
    ANTHROPIC_MODEL, ZEP_API_KEY, VOICE_ENABLED, TELEGRAM_BOT_TOKEN,
    SEARCH_LIMIT
)
from .validators import validate_response
from .services.message_logger import log_message

# Опциональный импорт голосового сервиса
try:
    from .voice.voice_service import VoiceService
    VOICE_SERVICE_AVAILABLE = True
except ImportError as e:
    VoiceService = None
    VOICE_SERVICE_AVAILABLE = False
    print(f"⚠️ VoiceService недоступен: {e}")

# Опциональный импорт Knowledge Search Service (Graphiti)
try:
    from .services.knowledge_search import get_knowledge_search_service
    KNOWLEDGE_SEARCH_AVAILABLE = True
except ImportError as e:
    get_knowledge_search_service = None
    KNOWLEDGE_SEARCH_AVAILABLE = False
    logger.warning(f"⚠️ Knowledge Search Service недоступен: {e}")

# Настройка логирования
logger = logging.getLogger(__name__)


class TextilProAgent:
    def __init__(self):
        # Инициализируем OpenAI клиент если API ключ доступен
        print(f"🔍 OPENAI_API_KEY: {'✅ Установлен' if OPENAI_API_KEY else '❌ Отсутствует'}")
        if OPENAI_API_KEY:
            print(f"🔍 Длина ключа: {len(OPENAI_API_KEY)} символов")
            print(f"🔍 Префикс: {OPENAI_API_KEY[:15]}...")
            try:
                print("🔄 Пытаемся создать AsyncOpenAI клиент...")
                self.openai_client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)
                print("✅ OpenAI клиент инициализирован")
                logger.info("✅ OpenAI клиент инициализирован успешно")
            except Exception as e:
                print(f"❌ Ошибка инициализации OpenAI: {type(e).__name__}: {e}")
                logger.error(f"❌ Ошибка инициализации OpenAI: {type(e).__name__}: {e}")
                import traceback
                traceback.print_exc()
                self.openai_client = None
        else:
            self.openai_client = None
            print("⚠️ OpenAI API ключ не найден")
            logger.warning("⚠️ OpenAI API ключ не найден в переменных окружения")
            
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
    
    async def search_knowledge_base(self, query: str, limit: int = 5) -> tuple:
        """
        Поиск релевантной информации в базе знаний

        Использует Graphiti hybrid search:
        1. Semantic search - векторный поиск по embeddings
        2. Full-text search - BM25 keyword matching
        3. Graph traversal - поиск по relationships
        4. Local files fallback (встроено в Graphiti) - MD файлы

        Returns:
            tuple: (context: str, sources: List[str], search_results: List[SearchResult])
        """

        # ====================
        # STRATEGY 1: Knowledge Search (Qdrant/Graphiti)
        # ====================
        if KNOWLEDGE_SEARCH_AVAILABLE:
            try:
                knowledge_service = get_knowledge_search_service()

                # Проверка доступности систем
                if knowledge_service.use_qdrant and knowledge_service.qdrant_enabled:
                    logger.info(f"🔵 Поиск через Qdrant Vector DB: '{query[:50]}...'")
                elif knowledge_service.graphiti_enabled:
                    logger.info(f"🟢 Поиск через Graphiti Knowledge Graph: '{query[:50]}...'")
                else:
                    logger.info("⚪ Ни одна из систем поиска не доступна")

                # Определяем оптимальную стратегию поиска
                from .services.knowledge_search import SearchStrategy
                strategy = knowledge_service.route_query(query)
                logger.info(f"🎯 Выбрана стратегия: {strategy}")

                # Выполняем поиск
                search_results = await knowledge_service.search(
                    query=query,
                    strategy=strategy,
                    limit=limit,
                    min_relevance=0.3  # Снижен threshold для лучшего поиска
                )

                if search_results:
                    # Форматируем контекст для LLM (увеличен лимит для детальных ответов)
                    context = knowledge_service.format_context_for_llm(
                        results=search_results,
                        max_length=15000  # Увеличено с 3000 для ~20 results × 750 chars
                    )

                    # ДИАГНОСТИЧЕСКОЕ ЛОГИРОВАНИЕ
                    raw_total_chars = sum(len(r.content) for r in search_results)
                    logger.info(f"📏 Formatted context length: {len(context)} chars")
                    logger.info(f"📏 Raw results total chars: {raw_total_chars}")
                    logger.info(f"📏 Results count: {len(search_results)}")
                    if len(context) < 500:
                        logger.warning(f"⚠️ ОЧЕНЬ КОРОТКИЙ КОНТЕКСТ! Content: '{context[:500]}...'")

                    # Извлекаем источники
                    sources_used = [result.source for result in search_results]

                    logger.info(f"✅ Найдено {len(search_results)} релевантных фрагментов")
                    return context, sources_used, search_results
                else:
                    logger.info("📭 Не нашли релевантных результатов")

            except Exception as e:
                logger.warning(f"⚠️ Ошибка knowledge search: {e}")

        # Если поиск недоступен или не нашёл результатов, возвращаем пустой результат
        logger.info("📭 База знаний недоступна или не нашла релевантной информации")
        return "", [], []
    
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
        """
        Роутер LLM запросов с fallback между OpenAI и Anthropic

        ⚠️ VERCEL SERVERLESS OPTIMIZATION:
        - Timeout 8s для AI запросов (Vercel Hobby limit: 10s, оставляем 2s буфер)
        - Автоматический fallback на Anthropic при timeout OpenAI
        """

        # Timeout для Vercel serverless (8s, оставляя 2s буфер для 10s limit)
        AI_REQUEST_TIMEOUT = 15.0  # Увеличено с 8s (timeout для больших контекстов)

        # Сначала пробуем OpenAI
        if self.openai_client:
            try:
                logger.info(f"🤖 Пытаемся использовать OpenAI (модель: {OPENAI_MODEL}, timeout: {AI_REQUEST_TIMEOUT}s)")

                # Обёртываем в asyncio.wait_for для timeout
                response = await asyncio.wait_for(
                    self.openai_client.chat.completions.create(
                        model=OPENAI_MODEL,  # Явно фиксируем gpt-4o-mini (быстрее)
                        messages=messages,
                        max_tokens=max_tokens,
                        temperature=temperature
                    ),
                    timeout=AI_REQUEST_TIMEOUT
                )

                # КРИТИЧЕСКИ ВАЖНО: Логируем фактически использованную модель
                actual_model = response.model
                logger.info(f"📊 Запрошенная модель: {OPENAI_MODEL}")
                logger.info(f"📊 Фактическая модель: {actual_model}")

                if OPENAI_MODEL != actual_model:
                    logger.warning(f"⚠️ НЕСООТВЕТСТВИЕ МОДЕЛЕЙ! Запрошена '{OPENAI_MODEL}', но использована '{actual_model}'")

                result = response.choices[0].message.content
                self.current_model = actual_model  # Track actual model used
                logger.info(f"✅ OpenAI ответ получен (модель: {actual_model}, tokens: {response.usage.total_tokens})")
                return result

            except asyncio.TimeoutError:
                logger.warning(f"⏱️ OpenAI timeout после {AI_REQUEST_TIMEOUT}s - переключаемся на Anthropic")
                print(f"⏱️ OpenAI timeout после {AI_REQUEST_TIMEOUT}s")

            except Exception as e:
                logger.error(f"❌ Ошибка OpenAI: {e}")
                print(f"❌ OpenAI недоступен: {e}")

        # Fallback на Anthropic
        if self.anthropic_client:
            try:
                logger.info(f"🤖 Fallback на Anthropic Claude (timeout: {AI_REQUEST_TIMEOUT}s)")

                # Конвертируем сообщения для Anthropic API
                system_message = ""
                user_messages = []

                for msg in messages:
                    if msg["role"] == "system":
                        system_message = msg["content"]
                    else:
                        user_messages.append(msg)

                # Обёртываем в asyncio.wait_for для timeout
                response = await asyncio.wait_for(
                    self.anthropic_client.messages.create(
                        model=ANTHROPIC_MODEL,
                        max_tokens=max_tokens,
                        temperature=temperature,
                        system=system_message,
                        messages=user_messages
                    ),
                    timeout=AI_REQUEST_TIMEOUT
                )

                result = response.content[0].text
                self.current_model = ANTHROPIC_MODEL  # Track which model was used
                logger.info("✅ Anthropic ответ получен")
                return result

            except asyncio.TimeoutError:
                logger.error(f"⏱️ Anthropic timeout после {AI_REQUEST_TIMEOUT}s")
                raise Exception(f"AI запрос превысил {AI_REQUEST_TIMEOUT}s timeout. Попробуйте упростить запрос или обратитесь позже.")

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
            logger.info(f"🔎 Вызов search_knowledge_base() для запроса: '{user_message[:50]}...'")
            knowledge_context, sources_used, search_results = await self.search_knowledge_base(user_message, limit=SEARCH_LIMIT)
            logger.info(f"✅ Поиск завершён: context={len(knowledge_context)} символов, sources={len(sources_used)}, results={len(search_results)}")

            # Пытаемся получить контекст из Zep Memory
            zep_context = await self.get_zep_memory_context(session_id)
            zep_history = await self.get_zep_recent_messages(session_id)

            # Добавляем контекст из базы знаний с ГИБКИМ RAG pattern
            # Проверяем что контекст содержит реальную информацию (не только заголовок)
            if knowledge_context and len(knowledge_context.strip()) > 100:
                logger.info(f"✅ Добавляем контекст из базы знаний в system prompt (длина: {len(knowledge_context)} символов)")
                system_prompt += f"""

⚠️ ПРАВИЛО ГЕНЕРАЦИИ ОТВЕТА:
Используй информацию из раздела БАЗА ЗНАНИЙ ниже как ОСНОВУ и ПРИМЕРЫ для твоего ответа.

✅ ТЫ МОЖЕШЬ:
- Комбинировать паттерны из разных примеров для создания детальных рекомендаций
- Синтезировать детальные ответы на основе методологии курса из примеров
- Использовать структуру и подход из примеров корректировок куратора

❌ ТЫ НЕ МОЖЕШЬ:
- Добавлять информацию которая ПРОТИВОРЕЧИТ методологии курса "Всепрощающая"
- Использовать общие психологические концепции НЕ из курса Натальи Игнатовой
- Игнорировать инструкции из instruction.json (длина ответа, количество примеров)

Если информации НЕДОСТАТОЧНО для детального ответа - скажи что нужно обратиться к Наталье.

=== БАЗА ЗНАНИЙ КУРСА "ВСЕПРОЩАЮЩАЯ" ===
{knowledge_context}
=== КОНЕЦ БАЗЫ ЗНАНИЙ ===

ВАЖНО: Следуй инструкциям по длине ответа и количеству примеров из instruction.json!
"""
            else:
                # Логируем почему контекст пустой/короткий
                if not knowledge_context:
                    logger.warning(f"⚠️ knowledge_context пустой (None или empty string)")
                elif len(knowledge_context.strip()) <= 100:
                    logger.warning(f"⚠️ knowledge_context слишком короткий ({len(knowledge_context)} символов)")
                    logger.warning(f"   Content preview: '{knowledge_context[:200]}...'")
                else:
                    logger.info("📭 Контекст из базы знаний пуст")
                # Если базы знаний нет - возвращаем fallback сообщение с DEBUG INFO
                user_name_display = user_name if user_name else "Дорогая"

                # Формируем DEBUG INFO для диагностики (если включено)
                from .config import DEBUG_INFO_ENABLED
                debug_info = ""

                if DEBUG_INFO_ENABLED:
                    debug_info = "\n\n---\n🔍 **DEBUG INFO:**\n"
                    debug_info += f"⚠️ **Status:** NO RESULTS FOUND\n"
                    debug_info += f"📚 Knowledge Base: ❌ Пустой результат поиска\n"
                    debug_info += f"📊 **Results:** 0 найдено (возможно threshold={0.3} слишком высокий или exception)\n"

                    # Информация о системе поиска
                    if KNOWLEDGE_SEARCH_AVAILABLE:
                        from bot.services.knowledge_search import get_knowledge_search_service
                        knowledge_service = get_knowledge_search_service()

                        if knowledge_service.use_supabase and knowledge_service.supabase_enabled:
                            debug_info += "🟣 **Search System:** SUPABASE Vector DB\n"
                        elif knowledge_service.use_qdrant and knowledge_service.qdrant_enabled:
                            debug_info += "🔵 **Search System:** QDRANT Vector DB\n"
                        elif knowledge_service.graphiti_enabled:
                            debug_info += "🟢 **Search System:** GRAPHITI Knowledge Graph\n"
                        else:
                            debug_info += "⚪ **Search System:** FALLBACK (local files)\n"

                    # Подсказка для пользователя
                    debug_info += f"💡 **Hint:** Попробуйте переформулировать вопрос или проверьте логи Railway\n"

                return f"{user_name_display}, по этому вопросу рекомендую написать в поддержку курса или обратиться к @support_ignatova 🌸{debug_info}"

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
                    bot_response = await self.call_llm(messages, max_tokens=2000, temperature=0.5)

                    # GPT сам добавляет источники согласно инструкции в system_prompt
                    # Автоматическое добавление убрано чтобы избежать дублирования

                    logger.info(f"✅ Ответ сгенерирован успешно (длина: {len(bot_response)} символов)")

                    # SUMMARY лог генерации
                    logger.info(f"""
📊 SUMMARY генерации ответа:
   • User message: '{user_message[:50]}{"..." if len(user_message) > 50 else ""}'
   • Knowledge base used: {'✅ Yes' if knowledge_context else '❌ No'}
   • Sources found: {len(sources_used)} - {', '.join(sources_used) if sources_used else 'N/A'}
   • Zep context: {'✅ Yes' if zep_context else '❌ No'}
   • Zep history: {'✅ Yes' if zep_history else '❌ No'}
   • Response length: {len(bot_response)} символов
   • Model: {getattr(self, 'current_model', 'unknown')}
""")

                    # Добавляем отладочную информацию в ответ бота (если включено)
                    from .config import DEBUG_INFO_ENABLED
                    import uuid

                    # Генерируем уникальный Message ID для трейсинга
                    message_id = f"M{uuid.uuid4().hex[:7]}"

                    if DEBUG_INFO_ENABLED:
                        # Компактный DEBUG INFO с Message ID для идентификации
                        debug_info = f"\n\n---\n🔍 **ID: #{message_id}**\n"

                        # Статус базы знаний и результаты
                        kb_status = "✅" if knowledge_context else "❌"

                        if search_results:
                            avg_score = sum(r.relevance_score for r in search_results) / len(search_results)
                            debug_info += f"📚 Knowledge: {kb_status} | 📊 Results: {len(search_results)} | ⭐ Relevance: {avg_score:.2f}\n"

                            # Разбивка по типам entities
                            entity_types = {}
                            for result in search_results:
                                entity_type = result.metadata.get('entity_type') or getattr(result, 'entity_type', 'unknown')
                                entity_types[entity_type] = entity_types.get(entity_type, 0) + 1

                            if entity_types:
                                types_str = ', '.join([f"{k}:{v}" for k, v in entity_types.items()])
                                debug_info += f"📁 Types: {types_str}\n"
                        else:
                            debug_info += f"📚 Knowledge: {kb_status} | 📊 Results: 0\n"

                        # Zep Memory статус
                        has_zep = (zep_context and len(str(zep_context).strip()) > 0) or \
                                  (zep_history and len(str(zep_history).strip()) > 0)
                        debug_info += f"🧠 Zep: {'✅' if has_zep else '❌'}\n"

                        bot_response += debug_info

                    # Логируем Message ID для поиска в логах
                    logger.info(f"🔗 Message ID: #{message_id} | Session: {session_id} | User: {user_name or 'Unknown'}")

                    # Сохраняем детальный лог в MySQL для анализа
                    entity_types_for_log = {}
                    avg_score_for_log = None
                    if search_results:
                        avg_score_for_log = sum(r.relevance_score for r in search_results) / len(search_results)
                        for result in search_results:
                            entity_type = result.metadata.get('entity_type') or getattr(result, 'entity_type', 'unknown')
                            entity_types_for_log[entity_type] = entity_types_for_log.get(entity_type, 0) + 1

                    # Вычисляем полную длину промпта
                    full_prompt_len = len(system_prompt) + len(user_message) + len(knowledge_context or "") + len(str(zep_context or "")) + len(str(zep_history or ""))

                    # Извлекаем user_id из session_id (формат: user_229838448)
                    extracted_user_id = session_id.replace("user_", "") if session_id and session_id.startswith("user_") else session_id

                    await log_message(
                        message_id=message_id,
                        user_id=extracted_user_id,
                        user_name=user_name,
                        session_id=session_id,
                        query=user_message,
                        search_results_count=len(search_results) if search_results else 0,
                        avg_relevance_score=avg_score_for_log,
                        entity_types=entity_types_for_log if entity_types_for_log else None,
                        sources=list(dict.fromkeys(sources_used)) if sources_used else None,
                        knowledge_context=knowledge_context,
                        zep_context=str(zep_context or "") + str(zep_history or ""),
                        full_prompt_length=full_prompt_len,
                        model_used=getattr(self, 'current_model', 'unknown'),
                        response_text=bot_response
                    )

                except Exception as llm_error:
                    logger.error(f"❌ Ошибка LLM: {type(llm_error).__name__}: {llm_error}")
                    logger.error(f"❌ Детали: {str(llm_error)}")
                    print(f"❌ КРИТИЧЕСКАЯ ОШИБКА LLM: {llm_error}")

                    # Улучшенный fallback - используем найденную информацию
                    if knowledge_context:
                        bot_response = f"⚠️ AI временно недоступен, но нашла информацию в базе знаний:\n\n{knowledge_context[:500]}"
                        if sources_used:
                            # Убираем дубликаты из sources
                            unique_sources = list(dict.fromkeys(sources_used))
                            sources_text = ", ".join(unique_sources[:3])  # Максимум 3 источника
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

            # === СОХРАНЕНИЕ В GRAPHITI: Temporal Knowledge Graph диалогов ===
            # ВРЕМЕННО ОТКЛЮЧЕНО для отладки - TODO: исправить и включить обратно
            # try:
            #     if KNOWLEDGE_SEARCH_AVAILABLE:
            #         knowledge_service = get_knowledge_search_service()
            #         if knowledge_service.graphiti_enabled:
            #             # Формируем episode из диалога
            #             user_name_display = user_name or "Пользователь"
            #             episode_content = f"Пользователь ({user_name_display}): {user_message}\n\nАссистент (Анастасия): {bot_response}"
            #
            #             # Добавляем episode в knowledge graph
            #             success, episode_id = await knowledge_service.graphiti_service.add_episode(
            #                 content=episode_content,
            #                 episode_type="conversation",
            #                 metadata={
            #                     "session_id": session_id,
            #                     "user_name": user_name_display,
            #                     "timestamp": datetime.utcnow().isoformat()
            #                 },
            #                 source_description=f"Telegram conversation with {user_name_display}"
            #             )
            #
            #             if success:
            #                 logger.info(f"✅ Episode сохранён в Graphiti: {episode_id}")
            #             else:
            #                 logger.warning(f"⚠️ Не удалось сохранить episode в Graphiti: {episode_id}")
            # except Exception as graphiti_error:
            #     # Не критично - если Graphiti недоступен, бот продолжает работать
            #     logger.warning(f"⚠️ Graphiti недоступен, диалог не сохранён в knowledge graph: {graphiti_error}")

            # === ВАЛИДАЦИЯ ОТВЕТА ПЕРЕД ОТПРАВКОЙ ===
            validation_result = validate_response(bot_response, student_name=user_name)

            if not validation_result["valid"]:
                logger.error(f"❌ ВАЛИДАЦИЯ НЕ ПРОШЛА: {validation_result['errors']}")
                # Логируем проблемный ответ для анализа
                logger.error(f"Проблемный ответ:\n{bot_response}")

            if validation_result["warnings"]:
                logger.warning(f"⚠️ Предупреждения валидации: {validation_result['warnings']}")

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