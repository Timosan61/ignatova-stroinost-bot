"""
🧠 Memory управление для ignatova-stroinost-bot
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from zep_cloud.client import AsyncZep
from zep_cloud.types import Message

logger = logging.getLogger(__name__)

class MemoryManager:
    """Класс для управления памятью диалогов через Zep Cloud"""
    
    def __init__(self, zep_api_key: str = None):
        self.zep_client = None
        self.local_sessions = {}  # Fallback локальное хранилище
        
        if zep_api_key and zep_api_key != "test_key":
            try:
                self.zep_client = AsyncZep(api_key=zep_api_key)
                print(f"✅ Zep клиент инициализирован")
                logger.info(f"✅ Zep Memory клиент инициализирован")
            except Exception as e:
                print(f"❌ Ошибка инициализации Zep: {e}")
                logger.error(f"❌ Ошибка инициализации Zep: {e}")
        else:
            print("⚠️ ZEP_API_KEY не установлен, используется локальная память")
            logger.warning("⚠️ ZEP_API_KEY не установлен, используется локальная память")
    
    @property
    def is_available(self) -> bool:
        """Проверяет доступность Zep клиента"""
        return self.zep_client is not None
    
    @property
    def memory_mode(self) -> str:
        """Возвращает режим работы памяти"""
        return "Zep Cloud" if self.is_available else "Local Memory"
    
    async def add_conversation(self, session_id: str, user_message: str, bot_response: str, user_name: str = None) -> bool:
        """Добавляет обмен сообщениями в память"""
        if not self.is_available:
            logger.info(f"⚠️ Zep недоступен, используем локальную память для {session_id}")
            self._add_to_local_memory(session_id, user_message, bot_response)
            return False
            
        try:
            # Используем имя пользователя или ID для роли
            user_role = user_name if user_name else f"User_{session_id.split('_')[-1][:6]}"
            
            messages = [
                Message(
                    role=user_role,
                    role_type="user",
                    content=user_message
                ),
                Message(
                    role="Анастасия",
                    role_type="assistant",
                    content=bot_response
                )
            ]
            
            await self.zep_client.memory.add(session_id=session_id, messages=messages)
            logger.info(f"✅ Сообщения добавлены в Zep для сессии {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка добавления в Zep: {type(e).__name__}: {e}")
            # Fallback на локальную память
            self._add_to_local_memory(session_id, user_message, bot_response)
            return False
    
    async def get_context(self, session_id: str) -> str:
        """Получает контекст из памяти"""
        if not self.is_available:
            logger.info(f"⚠️ Zep недоступен, используем локальную историю для {session_id}")
            return self._get_local_history(session_id)
            
        try:
            memory = await self.zep_client.memory.get(session_id=session_id)
            context = memory.context if memory.context else ""
            logger.info(f"✅ Получен контекст из Zep для {session_id}, длина: {len(context)}")
            return context
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения контекста из Zep: {type(e).__name__}: {e}")
            return self._get_local_history(session_id)
    
    async def get_recent_messages(self, session_id: str, limit: int = 6) -> str:
        """Получает последние сообщения из памяти"""
        if not self.is_available:
            return self._get_local_history(session_id, limit)
            
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
            logger.error(f"❌ Ошибка получения сообщений из Zep: {e}")
            return self._get_local_history(session_id, limit)
    
    async def ensure_user_exists(self, user_id: str, user_data: Dict[str, Any] = None) -> bool:
        """Создает пользователя в Zep если его еще нет"""
        if not self.is_available:
            return False
            
        try:
            # Проверяем существование пользователя
            try:
                await self.zep_client.user.get(user_id=user_id)
                logger.info(f"✅ Пользователь {user_id} уже существует в Zep")
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
                    'source': user_info.get('source', 'telegram'),
                    'created_at': datetime.now().isoformat()
                }
            )
            logger.info(f"✅ Создан новый пользователь в Zep: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания пользователя в Zep: {e}")
            return False
    
    async def ensure_session_exists(self, session_id: str, user_id: str) -> bool:
        """Создает сессию в Zep если ее еще нет"""
        if not self.is_available:
            return False
            
        try:
            await self.zep_client.memory.add_session(
                session_id=session_id,
                user_id=user_id,
                metadata={
                    'channel': 'telegram',
                    'created_at': datetime.now().isoformat()
                }
            )
            logger.info(f"✅ Создана сессия в Zep: {session_id}")
            return True
            
        except Exception as e:
            # Сессия может уже существовать или будет создана автоматически
            logger.info(f"ℹ️ Сессия {session_id} возможно уже существует")
            return True
    
    def _add_to_local_memory(self, session_id: str, user_message: str, bot_response: str):
        """Резервное локальное хранение"""
        if session_id not in self.local_sessions:
            self.local_sessions[session_id] = []
        
        self.local_sessions[session_id].append({
            "user": user_message,
            "assistant": bot_response,
            "timestamp": datetime.now().isoformat()
        })
        
        # Ограничиваем историю 10 сообщениями
        if len(self.local_sessions[session_id]) > 10:
            self.local_sessions[session_id] = self.local_sessions[session_id][-10:]
    
    def _get_local_history(self, session_id: str, limit: int = 6) -> str:
        """Получает историю из локального хранилища"""
        if session_id not in self.local_sessions:
            return ""
        
        history = []
        for exchange in self.local_sessions[session_id][-limit:]:
            history.append(f"Пользователь: {exchange['user']}")
            history.append(f"Ассистент: {exchange['assistant']}")
        
        return "\n".join(history) if history else ""
    
    def get_stats(self) -> Dict[str, Any]:
        """Получает статистику памяти"""
        return {
            "memory_mode": self.memory_mode,
            "zep_available": self.is_available,
            "local_sessions_count": len(self.local_sessions),
            "local_sessions": list(self.local_sessions.keys()) if self.local_sessions else []
        }