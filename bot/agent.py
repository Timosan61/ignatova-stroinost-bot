import json
import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Any

import openai
from zep_cloud.client import AsyncZep
from zep_cloud.types import Message

from .config import INSTRUCTION_FILE, OPENAI_API_KEY, OPENAI_MODEL, ZEP_API_KEY

# Настройка логирования
logger = logging.getLogger(__name__)


class TextilProAgent:
    def __init__(self):
        # Инициализируем OpenAI клиент если API ключ доступен
        if OPENAI_API_KEY:
            self.openai_client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)
            print("✅ OpenAI клиент инициализирован")
        else:
            self.openai_client = None
            print("⚠️ OpenAI API ключ не найден, используется упрощенный режим")
        
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
            
            # Временная заглушка для тестирования
            if self.openai_client is None:
                # Простая логика ответов без OpenAI
                user_message_lower = user_message.lower()
                
                if any(word in user_message_lower for word in ['привет', 'hello', 'hi', 'здравствуй']):
                    bot_response = "👋 Привет! Меня зовут Анастасия, я консультант Textile Pro. Чем могу помочь?"
                elif any(word in user_message_lower for word in ['цена', 'стоимость', 'сколько']):
                    bot_response = "💰 Цены зависят от объема и типа продукции. Расскажите подробнее о ваших потребностях - количество, тип одежды, материалы."
                elif any(word in user_message_lower for word in ['ткань', 'материал', 'хлопок', 'полиэстер']):
                    bot_response = "🧵 У нас широкий выбор тканей и материалов! Расскажите какой именно материал вас интересует - хлопок, полиэстер, смесовые ткани?"
                elif any(word in user_message_lower for word in ['китай', 'china', 'производство']):
                    bot_response = "🏭 Мы работаем с проверенными фабриками в Китае, Индии и Бангладеш. Обеспечиваем полный цикл производства с контролем качества."
                elif any(word in user_message_lower for word in ['доставка', 'логистика', 'shipping']):
                    bot_response = "🚢 Организуем доставку морским, авиа и железнодорожным транспортом. Время доставки 15-45 дней в зависимости от способа."
                elif any(word in user_message_lower for word in ['качество', 'контроль', 'проверка']):
                    bot_response = "✅ У нас строгий контроль качества на всех этапах. Предоставляем фото отчеты, можем организовать инспекцию третьей стороной."
                else:
                    bot_response = f"Поняла ваш вопрос! Отличный вопрос о текстильном производстве.\n\nПодготовлю детальный ответ специально для вас. Минуточку!\n\nАнастасия, Textil PRO"
            else:
                response = await self.openai_client.chat.completions.create(
                    model=OPENAI_MODEL,
                    messages=messages,
                    max_tokens=1000,
                    temperature=0.7
                )
                bot_response = response.choices[0].message.content
            
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
    
    def get_instruction_info(self) -> dict:
        """Получает информацию о текущих инструкциях для админ-панели"""
        return {
            "last_updated": self.instruction.get("last_updated", "неизвестно"),
            "system_instruction_length": len(self.instruction.get("system_instruction", "")),
            "welcome_message": self.instruction.get("welcome_message", ""),
            "openai_enabled": self.openai_client is not None,
            "zep_enabled": self.zep_client is not None
        }


agent = TextilProAgent()