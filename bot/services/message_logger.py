"""
Message Logger Service

Сервис для сохранения детальных логов обработки сообщений в MySQL.
Позволяет найти по Message ID полную информацию о запросе для анализа.

Usage:
    from bot.services.message_logger import log_message, get_message_log

    # Сохранить лог
    await log_message(
        message_id="M624aa39",
        user_id="123456",
        query="сколько стоит курс?",
        ...
    )

    # Получить лог по ID
    log = await get_message_log("M624aa39")
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)

# Import database components
try:
    from bot.database import SessionLocal, MessageLog, DATABASE_ENABLED
    DB_AVAILABLE = DATABASE_ENABLED
except ImportError as e:
    logger.warning(f"⚠️ Database not available for message logging: {e}")
    DB_AVAILABLE = False
    SessionLocal = None
    MessageLog = None


async def log_message(
    message_id: str,
    user_id: Optional[str] = None,
    user_name: Optional[str] = None,
    session_id: Optional[str] = None,
    query: Optional[str] = None,
    search_results_count: int = 0,
    avg_relevance_score: Optional[float] = None,
    entity_types: Optional[Dict[str, int]] = None,
    sources: Optional[List[str]] = None,
    knowledge_context: Optional[str] = None,
    zep_context: Optional[str] = None,
    full_prompt_length: Optional[int] = None,
    model_used: Optional[str] = None,
    response_text: Optional[str] = None,
    error_message: Optional[str] = None
) -> bool:
    """
    Сохранить детальный лог обработки сообщения в MySQL.

    Args:
        message_id: Уникальный ID сообщения (формат: M624aa39)
        user_id: Telegram user ID
        user_name: Имя пользователя
        session_id: Session ID для Zep
        query: Оригинальный запрос пользователя
        search_results_count: Количество найденных результатов
        avg_relevance_score: Средний score релевантности
        entity_types: Breakdown по типам entities {"lesson": 3, "faq": 2}
        sources: Список использованных источников
        knowledge_context: Контекст из базы знаний (embeddings)
        zep_context: Контекст из Zep памяти
        full_prompt_length: Полная длина промпта в символах
        model_used: Использованная модель
        response_text: Ответ модели
        error_message: Сообщение об ошибке если была

    Returns:
        True если лог сохранён успешно, False в противном случае
    """
    if not DB_AVAILABLE:
        logger.debug(f"📝 Message logging skipped (DB not available): {message_id}")
        return False

    try:
        db = SessionLocal()
        try:
            # Создаём запись лога
            log_entry = MessageLog(
                message_id=message_id,
                user_id=user_id,
                user_name=user_name,
                session_id=session_id,
                query=query,
                search_results_count=search_results_count,
                avg_relevance_score=avg_relevance_score,
                entity_types=entity_types,
                sources=sources,
                knowledge_context=knowledge_context,
                zep_context=zep_context,
                full_prompt_length=full_prompt_length,
                model_used=model_used,
                response_text=response_text,
                response_length=len(response_text) if response_text else 0,
                error_message=error_message,
                created_at=datetime.utcnow()
            )

            db.add(log_entry)
            db.commit()

            logger.info(f"📝 Message logged: #{message_id} | User: {user_name or user_id} | Results: {search_results_count}")
            return True

        except Exception as e:
            db.rollback()
            logger.error(f"❌ Failed to log message {message_id}: {e}")
            return False
        finally:
            db.close()

    except Exception as e:
        logger.error(f"❌ Database error in log_message: {e}")
        return False


async def get_message_log(message_id: str) -> Optional[Dict[str, Any]]:
    """
    Получить лог сообщения по Message ID.

    Args:
        message_id: ID сообщения (формат: M624aa39)

    Returns:
        Dict с деталями обработки или None если не найден
    """
    if not DB_AVAILABLE:
        return None

    try:
        db = SessionLocal()
        try:
            # Поиск по message_id
            log_entry = db.query(MessageLog).filter(
                MessageLog.message_id == message_id
            ).first()

            if not log_entry:
                return None

            return {
                "message_id": log_entry.message_id,
                "user_id": log_entry.user_id,
                "user_name": log_entry.user_name,
                "session_id": log_entry.session_id,
                "query": log_entry.query,
                "search_results_count": log_entry.search_results_count,
                "avg_relevance_score": log_entry.avg_relevance_score,
                "entity_types": log_entry.entity_types,
                "sources": log_entry.sources,
                "knowledge_context": log_entry.knowledge_context,
                "zep_context": log_entry.zep_context,
                "full_prompt_length": log_entry.full_prompt_length,
                "model_used": log_entry.model_used,
                "response_text": log_entry.response_text,
                "response_length": log_entry.response_length,
                "error_message": log_entry.error_message,
                "created_at": log_entry.created_at.isoformat() if log_entry.created_at else None
            }

        finally:
            db.close()

    except Exception as e:
        logger.error(f"❌ Failed to get message log {message_id}: {e}")
        return None


async def get_recent_logs(limit: int = 20) -> List[Dict[str, Any]]:
    """
    Получить последние логи сообщений.

    Args:
        limit: Максимальное количество записей

    Returns:
        List of message logs (краткая информация)
    """
    if not DB_AVAILABLE:
        return []

    try:
        db = SessionLocal()
        try:
            logs = db.query(MessageLog).order_by(
                MessageLog.created_at.desc()
            ).limit(limit).all()

            return [
                {
                    "message_id": log.message_id,
                    "user_name": log.user_name,
                    "query": log.query[:100] + "..." if log.query and len(log.query) > 100 else log.query,
                    "search_results_count": log.search_results_count,
                    "avg_relevance_score": log.avg_relevance_score,
                    "model_used": log.model_used,
                    "has_error": bool(log.error_message),
                    "created_at": log.created_at.isoformat() if log.created_at else None
                }
                for log in logs
            ]

        finally:
            db.close()

    except Exception as e:
        logger.error(f"❌ Failed to get recent logs: {e}")
        return []
