"""
🔍 Debug endpoints для ignatova-stroinost-bot
"""

import os
import logging
from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter

# Import message logger
try:
    from bot.services.message_logger import get_message_log, get_recent_logs
    MESSAGE_LOGGER_AVAILABLE = True
except ImportError:
    MESSAGE_LOGGER_AVAILABLE = False
    get_message_log = None
    get_recent_logs = None

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/debug", tags=["debug"])

def create_debug_router(agent=None, business_handler=None) -> APIRouter:
    """Создает router с debug endpoints"""
    
    @router.get("/zep-status")
    async def get_zep_status():
        """Проверить статус Zep Memory"""
        if not agent:
            return {
                "status": "error",
                "error": "AI модуль не загружен",
                "zep_client_initialized": False,
                "memory_mode": "Unavailable"
            }
        
        try:
            zep_api_key = os.getenv('ZEP_API_KEY', '')
            zep_client = agent.zep_client if hasattr(agent, 'zep_client') else None
            
            return {
                "status": "success",
                "zep_api_key_set": bool(zep_api_key and zep_api_key != "test_key"),
                "zep_api_key_length": len(zep_api_key) if zep_api_key else 0,
                "zep_api_key_preview": f"{zep_api_key[:8]}..." if zep_api_key else "Not set",
                "zep_client_initialized": zep_client is not None,
                "memory_mode": "Zep Cloud" if zep_client else "Local Memory",
                "ai_agent_loaded": True,
                "current_time": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "status": "error", 
                "error": str(e),
                "zep_client_initialized": False,
                "memory_mode": "Error"
            }

    @router.get("/business-owners")
    async def get_business_owners():
        """Статус Business Connection владельцев"""
        if not business_handler:
            return {
                "status": "error",
                "error": "Business handler не инициализирован"
            }
        
        return business_handler.get_status()

    @router.get("/last-updates")
    async def get_last_updates():
        """Последние обновления (заглушка для совместимости)"""
        return {
            "status": "success",
            "message": "Endpoint перенесен в debug endpoints",
            "current_time": datetime.now().isoformat()
        }

    @router.get("/logs")
    async def get_recent_logs():
        """Получить последние логи"""
        try:
            log_file = "logs/bot.log"
            if os.path.exists(log_file):
                with open(log_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    recent_lines = lines[-20:] if len(lines) > 20 else lines
                    return {
                        "status": "success",
                        "logs": [line.strip() for line in recent_lines],
                        "total_lines": len(lines)
                    }
            else:
                return {
                    "status": "error",
                    "error": "Log file not found"
                }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    @router.get("/voice-logs")
    async def get_voice_logs():
        """Получить логи голосовых сообщений"""
        try:
            log_file = "logs/bot.log"
            voice_lines = []
            
            if os.path.exists(log_file):
                with open(log_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    voice_keywords = ['голос', 'voice', '🎤', '🔑', 'file_id', 'транскри', 'whisper', 'audio']
                    for line in lines:
                        if any(keyword.lower() in line.lower() for keyword in voice_keywords):
                            voice_lines.append(line.strip())
                    
                    recent_voice_lines = voice_lines[-30:] if len(voice_lines) > 30 else voice_lines
                    
                    return {
                        "status": "success",
                        "voice_logs": recent_voice_lines,
                        "total_voice_logs": len(voice_lines),
                        "voice_service_status": "active" if agent and hasattr(agent, 'voice_service') else "inactive"
                    }
            else:
                return {
                    "status": "error",
                    "error": "Log file not found"
                }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    @router.get("/memory/{session_id}")
    async def get_session_memory(session_id: str):
        """Получить память сессии (для отладки)"""
        if not agent or not hasattr(agent, 'zep_client') or not agent.zep_client:
            return {
                "status": "error",
                "error": "Zep не доступен"
            }
        
        try:
            memory = await agent.zep_client.memory.get(session_id=session_id)
            
            return {
                "status": "success",
                "session_id": session_id,
                "messages_count": len(memory.messages) if memory.messages else 0,
                "context_length": len(memory.context) if memory.context else 0,
                "context_preview": memory.context[:200] + "..." if memory.context and len(memory.context) > 200 else memory.context,
                "recent_messages": [
                    {
                        "role": msg.role,
                        "role_type": msg.role_type,
                        "content": msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
                    }
                    for msg in (memory.messages[-5:] if memory.messages else [])
                ]
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }

    # === MESSAGE LOGS ENDPOINTS ===

    @router.get("/message/{message_id}")
    async def get_message_details(message_id: str):
        """
        Получить детальную информацию о сообщении по Message ID.

        Использование: GET /debug/message/M624aa39

        Возвращает:
        - Оригинальный запрос пользователя
        - Найденный контекст из embeddings
        - Результаты поиска (scores, entity types)
        - Контекст из Zep памяти
        - Ответ модели
        """
        if not MESSAGE_LOGGER_AVAILABLE:
            return {
                "status": "error",
                "error": "Message logger не доступен"
            }

        # Убираем # из message_id если есть
        clean_id = message_id.lstrip('#')

        try:
            log_data = await get_message_log(clean_id)

            if not log_data:
                return {
                    "status": "not_found",
                    "message_id": clean_id,
                    "error": f"Лог с ID '{clean_id}' не найден"
                }

            return {
                "status": "success",
                "data": log_data
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }

    @router.get("/messages/recent")
    async def get_recent_message_logs(limit: int = 20):
        """
        Получить последние логи сообщений.

        Использование: GET /debug/messages/recent?limit=20
        """
        if not MESSAGE_LOGGER_AVAILABLE:
            return {
                "status": "error",
                "error": "Message logger не доступен"
            }

        try:
            logs = await get_recent_logs(limit=min(limit, 100))

            return {
                "status": "success",
                "count": len(logs),
                "logs": logs
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }

    return router