"""
FastAPI endpoints for accessing stored telegram conversations.
Adapted from GPTIFOBIZ architecture.
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from bot.database.database import get_db, DATABASE_ENABLED
from bot.database.models import TelegramChat, TelegramMessage

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api",
    tags=["messages"],
    responses={404: {"description": "Not found"}},
)


@router.get("/health/db")
async def check_database_health():
    """Check if database is enabled and accessible"""
    if not DATABASE_ENABLED:
        return {
            "status": "disabled",
            "message": "Database is not configured"
        }

    return {
        "status": "enabled",
        "message": "Database is configured and running"
    }


@router.get("/chats")
async def get_all_chats(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=200, description="Number of records to return"),
    business_only: bool = Query(False, description="Filter only Business API chats"),
    db: Session = Depends(get_db)
):
    """
    Get all chats with pagination.

    - **skip**: Number of records to skip (default: 0)
    - **limit**: Max records to return (1-200, default: 50)
    - **business_only**: Filter only Business API chats
    """
    if not DATABASE_ENABLED or db is None:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        query = db.query(TelegramChat)

        if business_only:
            query = query.filter(TelegramChat.is_business_chat == True)

        total = query.count()
        chats = query.order_by(desc(TelegramChat.last_message_at)).offset(skip).limit(limit).all()

        return {
            "total": total,
            "skip": skip,
            "limit": limit,
            "chats": [
                {
                    "id": chat.id,
                    "telegram_chat_id": chat.telegram_chat_id,
                    "username": chat.username,
                    "first_name": chat.first_name,
                    "last_name": chat.last_name,
                    "chat_type": chat.chat_type,
                    "is_business_chat": chat.is_business_chat,
                    "total_messages": chat.total_messages,
                    "total_voice_messages": chat.total_voice_messages,
                    "last_message_at": chat.last_message_at.isoformat() if chat.last_message_at else None,
                    "created_at": chat.created_at.isoformat() if chat.created_at else None,
                }
                for chat in chats
            ]
        }

    except Exception as e:
        logger.error(f"Error fetching chats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chats/{chat_id}")
async def get_chat_details(
    chat_id: int,
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a specific chat.

    - **chat_id**: Internal database ID of the chat
    """
    if not DATABASE_ENABLED or db is None:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        chat = db.query(TelegramChat).filter(TelegramChat.id == chat_id).first()

        if not chat:
            raise HTTPException(status_code=404, detail="Chat not found")

        return {
            "id": chat.id,
            "telegram_chat_id": chat.telegram_chat_id,
            "username": chat.username,
            "first_name": chat.first_name,
            "last_name": chat.last_name,
            "phone": chat.phone,
            "chat_type": chat.chat_type,
            "title": chat.title,
            "bio": chat.bio,
            "is_business_chat": chat.is_business_chat,
            "business_connection_id": chat.business_connection_id,
            "total_messages": chat.total_messages,
            "total_voice_messages": chat.total_voice_messages,
            "last_message_at": chat.last_message_at.isoformat() if chat.last_message_at else None,
            "created_at": chat.created_at.isoformat() if chat.created_at else None,
            "updated_at": chat.updated_at.isoformat() if chat.updated_at else None,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching chat {chat_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chats/{chat_id}/messages")
async def get_chat_messages(
    chat_id: int,
    skip: int = Query(0, ge=0, description="Number of messages to skip"),
    limit: int = Query(50, ge=1, le=200, description="Number of messages to return"),
    db: Session = Depends(get_db)
):
    """
    Get messages from a specific chat with pagination.

    - **chat_id**: Internal database ID of the chat
    - **skip**: Number of messages to skip (default: 0)
    - **limit**: Max messages to return (1-200, default: 50)
    """
    if not DATABASE_ENABLED or db is None:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        # Verify chat exists
        chat = db.query(TelegramChat).filter(TelegramChat.id == chat_id).first()
        if not chat:
            raise HTTPException(status_code=404, detail="Chat not found")

        # Get messages
        total_messages = db.query(TelegramMessage).filter(TelegramMessage.chat_id == chat_id).count()
        messages = db.query(TelegramMessage).filter(
            TelegramMessage.chat_id == chat_id
        ).order_by(desc(TelegramMessage.created_at)).offset(skip).limit(limit).all()

        return {
            "chat_id": chat_id,
            "total_messages": total_messages,
            "skip": skip,
            "limit": limit,
            "messages": [
                {
                    "id": msg.id,
                    "telegram_message_id": msg.telegram_message_id,
                    "text": msg.text,
                    "voice_transcript": msg.voice_transcript,
                    "is_voice_message": msg.is_voice_message,
                    "sender_telegram_id": msg.sender_telegram_id,
                    "sender_username": msg.sender_username,
                    "sender_first_name": msg.sender_first_name,
                    "is_from_user": msg.is_from_user,
                    "is_from_business": msg.is_from_business,
                    "has_attachments": msg.has_attachments,
                    "attachments_meta": msg.attachments_meta,
                    "bot_response_text": msg.bot_response_text,
                    "ai_model_used": msg.ai_model_used,
                    "message_date": msg.message_date,
                    "created_at": msg.created_at.isoformat() if msg.created_at else None,
                }
                for msg in messages
            ]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching messages for chat {chat_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_statistics(db: Session = Depends(get_db)):
    """
    Get overall statistics about stored conversations.
    """
    if not DATABASE_ENABLED or db is None:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        # Chat statistics
        total_chats = db.query(TelegramChat).count()
        business_chats = db.query(TelegramChat).filter(TelegramChat.is_business_chat == True).count()

        # Message statistics
        total_messages = db.query(TelegramMessage).count()
        voice_messages = db.query(TelegramMessage).filter(TelegramMessage.is_voice_message == True).count()
        business_messages = db.query(TelegramMessage).filter(TelegramMessage.is_from_business == True).count()
        messages_with_attachments = db.query(TelegramMessage).filter(TelegramMessage.has_attachments == True).count()
        user_messages = db.query(TelegramMessage).filter(TelegramMessage.is_from_user == True).count()

        return {
            "chats": {
                "total": total_chats,
                "business": business_chats,
                "regular": total_chats - business_chats,
            },
            "messages": {
                "total": total_messages,
                "from_users": user_messages,
                "from_bot": total_messages - user_messages,
                "voice": voice_messages,
                "business": business_messages,
                "with_attachments": messages_with_attachments,
            }
        }

    except Exception as e:
        logger.error(f"Error fetching statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search")
async def search_messages(
    q: str = Query(..., min_length=2, description="Search query (minimum 2 characters)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """
    Search messages by text content or voice transcript.

    - **q**: Search query (minimum 2 characters)
    - **skip**: Number of results to skip
    - **limit**: Max results to return (1-200, default: 50)
    """
    if not DATABASE_ENABLED or db is None:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        search_pattern = f"%{q}%"

        # Search in both text and voice_transcript
        query = db.query(TelegramMessage).filter(
            (TelegramMessage.text.like(search_pattern)) |
            (TelegramMessage.voice_transcript.like(search_pattern))
        )

        total = query.count()
        messages = query.order_by(desc(TelegramMessage.created_at)).offset(skip).limit(limit).all()

        return {
            "query": q,
            "total_results": total,
            "skip": skip,
            "limit": limit,
            "messages": [
                {
                    "id": msg.id,
                    "chat_id": msg.chat_id,
                    "text": msg.text,
                    "voice_transcript": msg.voice_transcript,
                    "is_voice_message": msg.is_voice_message,
                    "sender_first_name": msg.sender_first_name,
                    "created_at": msg.created_at.isoformat() if msg.created_at else None,
                }
                for msg in messages
            ]
        }

    except Exception as e:
        logger.error(f"Error searching messages: {e}")
        raise HTTPException(status_code=500, detail=str(e))
