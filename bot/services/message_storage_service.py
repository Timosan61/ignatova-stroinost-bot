"""
Message storage service for saving Telegram conversations to MySQL database.
Provides methods to save chats and messages with retry logic and error handling.
Adapted from GPTIFOBIZ telegram_matching_service.
"""

import time
import logging
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, OperationalError

from bot.database.database import DATABASE_ENABLED, SessionLocal
from bot.database.models import TelegramChat, TelegramMessage

logger = logging.getLogger(__name__)


class MessageStorageService:
    """
    Service for storing Telegram chats and messages in MySQL database.
    Handles both regular and Business API messages.
    """

    def __init__(self):
        self.db_enabled = DATABASE_ENABLED
        if not self.db_enabled:
            logger.warning("Database is disabled. Message storage will be skipped.")

    async def save_or_update_chat(
        self,
        chat_data: Dict[str, Any],
        db: Optional[Session] = None
    ) -> Optional[TelegramChat]:
        """
        Save or update chat information.

        Args:
            chat_data: Dictionary containing chat information
                Required: 'id' (telegram chat_id)
                Optional: 'type', 'username', 'first_name', 'last_name',
                         'title', 'phone', 'bio', 'business_connection_id'
            db: Database session (optional, will create if not provided)

        Returns:
            TelegramChat instance if successful, None otherwise
        """
        if not self.db_enabled:
            return None

        close_session = False
        if db is None:
            db = SessionLocal()
            close_session = True

        try:
            telegram_chat_id = str(chat_data.get('id'))

            # Check if chat already exists
            existing_chat = db.query(TelegramChat).filter(
                TelegramChat.telegram_chat_id == telegram_chat_id
            ).first()

            if existing_chat:
                # Update existing chat
                existing_chat.chat_type = chat_data.get('type', existing_chat.chat_type)
                existing_chat.username = chat_data.get('username', existing_chat.username)
                existing_chat.first_name = chat_data.get('first_name', existing_chat.first_name)
                existing_chat.last_name = chat_data.get('last_name', existing_chat.last_name)
                existing_chat.title = chat_data.get('title', existing_chat.title)
                existing_chat.phone = chat_data.get('phone', existing_chat.phone)
                existing_chat.bio = chat_data.get('bio', existing_chat.bio)
                existing_chat.updated_at = datetime.utcnow()

                # Business API fields
                if chat_data.get('business_connection_id'):
                    existing_chat.is_business_chat = True
                    existing_chat.business_connection_id = chat_data.get('business_connection_id')

                db.commit()
                db.refresh(existing_chat)
                logger.info(f"Updated chat: {telegram_chat_id}")
                return existing_chat

            else:
                # Create new chat
                new_chat = TelegramChat(
                    telegram_chat_id=telegram_chat_id,
                    chat_type=chat_data.get('type', 'private'),
                    username=chat_data.get('username'),
                    first_name=chat_data.get('first_name'),
                    last_name=chat_data.get('last_name'),
                    phone=chat_data.get('phone'),
                    title=chat_data.get('title'),
                    bio=chat_data.get('bio'),
                    is_business_chat=bool(chat_data.get('business_connection_id')),
                    business_connection_id=chat_data.get('business_connection_id'),
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )

                db.add(new_chat)
                db.commit()
                db.refresh(new_chat)
                logger.info(f"Created new chat: {telegram_chat_id}")
                return new_chat

        except Exception as e:
            db.rollback()
            logger.error(f"Error saving/updating chat {chat_data.get('id')}: {e}")
            return None

        finally:
            if close_session:
                db.close()

    async def save_message(
        self,
        message_data: Dict[str, Any],
        chat: Optional[TelegramChat] = None,
        chat_id: Optional[str] = None,
        db: Optional[Session] = None
    ) -> Optional[TelegramMessage]:
        """
        Save a message to database with retry logic.

        Args:
            message_data: Dictionary containing message information
                Required: 'message_id', 'text' (or 'voice_transcript')
                Optional: 'from', 'is_from_business', 'business_connection_id',
                         'date', 'photo', 'document', 'video', etc.
            chat: TelegramChat instance (optional)
            chat_id: Telegram chat ID string (used if chat not provided)
            db: Database session (optional)

        Returns:
            TelegramMessage instance if successful, None otherwise
        """
        if not self.db_enabled:
            return None

        close_session = False
        if db is None:
            db = SessionLocal()
            close_session = True

        # Retry logic for database locks
        max_retries = 3
        retry_delay = 1  # seconds

        for attempt in range(max_retries):
            try:
                # Get or create chat if not provided
                if chat is None:
                    if chat_id is None:
                        logger.error("Either 'chat' or 'chat_id' must be provided")
                        return None

                    chat = db.query(TelegramChat).filter(
                        TelegramChat.telegram_chat_id == str(chat_id)
                    ).first()

                    if chat is None:
                        logger.error(f"Chat not found: {chat_id}")
                        return None

                # Extract message data
                telegram_message_id = str(message_data.get('message_id'))

                # Check for duplicate
                existing_message = db.query(TelegramMessage).filter(
                    TelegramMessage.chat_id == chat.id,
                    TelegramMessage.telegram_message_id == telegram_message_id
                ).first()

                if existing_message:
                    logger.debug(f"Message already exists: {telegram_message_id}")
                    return existing_message

                # Extract sender information
                sender = message_data.get('from', {})
                if isinstance(sender, dict):
                    sender_id = str(sender.get('id', ''))
                    sender_username = sender.get('username')
                    sender_first_name = sender.get('first_name')
                    sender_last_name = sender.get('last_name')
                else:
                    sender_id = ''
                    sender_username = None
                    sender_first_name = None
                    sender_last_name = None

                # Check for attachments
                has_attachments = any([
                    message_data.get('photo'),
                    message_data.get('document'),
                    message_data.get('video'),
                    message_data.get('audio'),
                    message_data.get('voice'),
                    message_data.get('video_note'),
                    message_data.get('sticker'),
                ])

                # Build attachments metadata
                attachments_meta = None
                if has_attachments:
                    attachments_meta = {}
                    for att_type in ['photo', 'document', 'video', 'audio', 'voice', 'video_note', 'sticker']:
                        if message_data.get(att_type):
                            attachments_meta[att_type] = True

                            # Add file details if available
                            att_data = message_data.get(att_type)
                            if isinstance(att_data, list) and len(att_data) > 0:
                                # For photos, get largest
                                att_data = max(att_data, key=lambda x: x.get('file_size', 0))

                            if isinstance(att_data, dict):
                                attachments_meta[f'{att_type}_file_id'] = att_data.get('file_id')
                                attachments_meta[f'{att_type}_file_size'] = att_data.get('file_size')

                # Determine message type
                is_voice = bool(message_data.get('voice_transcript'))
                is_from_user = message_data.get('is_from_user', True)

                # Create message record
                new_message = TelegramMessage(
                    chat_id=chat.id,
                    telegram_message_id=telegram_message_id,
                    text=message_data.get('text') or message_data.get('caption'),
                    voice_transcript=message_data.get('voice_transcript'),
                    sender_telegram_id=sender_id,
                    sender_username=sender_username,
                    sender_first_name=sender_first_name,
                    sender_last_name=sender_last_name,
                    is_from_user=is_from_user,
                    is_voice_message=is_voice,
                    is_from_business=message_data.get('is_from_business', False),
                    business_connection_id=message_data.get('business_connection_id'),
                    has_attachments=has_attachments,
                    attachments_meta=attachments_meta,
                    bot_response_text=message_data.get('bot_response'),
                    ai_model_used=message_data.get('ai_model'),
                    message_date=message_data.get('date'),
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )

                db.add(new_message)

                # Update chat statistics
                chat.total_messages = (chat.total_messages or 0) + 1
                if is_voice:
                    chat.total_voice_messages = (chat.total_voice_messages or 0) + 1
                chat.last_message_at = datetime.utcnow()
                chat.updated_at = datetime.utcnow()

                db.commit()
                db.refresh(new_message)

                logger.info(f"Saved message {telegram_message_id} to chat {chat.telegram_chat_id}")
                return new_message

            except (OperationalError, IntegrityError) as e:
                db.rollback()

                # Check if it's a lock error
                if 'Lock wait timeout' in str(e) or 'Deadlock' in str(e):
                    if attempt < max_retries - 1:
                        logger.warning(f"Database lock detected. Retrying in {retry_delay}s... (attempt {attempt + 1}/{max_retries})")
                        time.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                        continue
                    else:
                        logger.error(f"Failed to save message after {max_retries} retries: {e}")
                        return None
                else:
                    logger.error(f"Database error saving message: {e}")
                    return None

            except Exception as e:
                db.rollback()
                logger.error(f"Unexpected error saving message: {e}")
                return None

            finally:
                if close_session:
                    db.close()

        return None

    async def get_chat_by_telegram_id(
        self,
        telegram_chat_id: str,
        db: Optional[Session] = None
    ) -> Optional[TelegramChat]:
        """
        Get chat by Telegram chat ID.

        Args:
            telegram_chat_id: Telegram chat ID
            db: Database session (optional)

        Returns:
            TelegramChat instance if found, None otherwise
        """
        if not self.db_enabled:
            return None

        close_session = False
        if db is None:
            db = SessionLocal()
            close_session = True

        try:
            chat = db.query(TelegramChat).filter(
                TelegramChat.telegram_chat_id == str(telegram_chat_id)
            ).first()

            return chat

        except Exception as e:
            logger.error(f"Error getting chat {telegram_chat_id}: {e}")
            return None

        finally:
            if close_session:
                db.close()


# Global instance
message_storage = MessageStorageService()
