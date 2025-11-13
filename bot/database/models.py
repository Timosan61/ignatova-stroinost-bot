"""
SQLAlchemy models for storing Telegram conversations.
Adapted from GPTIFOBIZ architecture for Ignatova-Stroinost bot.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, JSON, Index
from sqlalchemy.orm import relationship
from bot.database.database import Base


class TelegramChat(Base):
    """
    Represents a Telegram chat/conversation.
    Stores information about users who interact with the bot.
    """
    __tablename__ = "telegram_chats"

    # Primary key
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # Telegram identifiers
    telegram_chat_id = Column(String(255), unique=True, nullable=False, index=True, comment="Unique Telegram chat ID")
    chat_type = Column(String(50), nullable=True, comment="Type: 'private', 'group', 'channel'")

    # User information
    username = Column(String(255), nullable=True, index=True, comment="Telegram @username")
    first_name = Column(String(255), nullable=True, comment="User's first name")
    last_name = Column(String(255), nullable=True, comment="User's last name")
    phone = Column(String(50), nullable=True, index=True, comment="User's phone number if available")

    # Business API specific
    is_business_chat = Column(Boolean, default=False, comment="Is this a Business API chat?")
    business_connection_id = Column(String(255), nullable=True, index=True, comment="Business connection ID")

    # Chat metadata
    title = Column(String(255), nullable=True, comment="Chat title (for groups/channels)")
    bio = Column(Text, nullable=True, comment="User bio/description")

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True, comment="When chat was first created")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, comment="When chat was last updated")
    last_message_at = Column(DateTime, nullable=True, index=True, comment="When last message was received")

    # Statistics
    total_messages = Column(Integer, default=0, comment="Total number of messages in this chat")
    total_voice_messages = Column(Integer, default=0, comment="Total number of voice messages")

    # Relationships
    messages = relationship("TelegramMessage", back_populates="chat", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<TelegramChat(id={self.id}, telegram_chat_id={self.telegram_chat_id}, username={self.username})>"


class TelegramMessage(Base):
    """
    Represents a single message in a Telegram chat.
    Stores both user messages and bot responses.
    """
    __tablename__ = "telegram_messages"

    # Primary key
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # Foreign key to chat
    chat_id = Column(Integer, ForeignKey("telegram_chats.id", ondelete="CASCADE"), nullable=False, index=True, comment="Reference to TelegramChat")

    # Telegram identifiers
    telegram_message_id = Column(String(255), nullable=False, index=True, comment="Telegram message ID")

    # Message content
    text = Column(Text, nullable=True, comment="Message text content")
    voice_transcript = Column(Text, nullable=True, comment="Transcribed text from voice message (via Whisper)")

    # Sender information
    sender_telegram_id = Column(String(255), nullable=True, index=True, comment="Sender's Telegram user ID")
    sender_username = Column(String(255), nullable=True, comment="Sender's @username")
    sender_first_name = Column(String(255), nullable=True, comment="Sender's first name")
    sender_last_name = Column(String(255), nullable=True, comment="Sender's last name")

    # Message type flags
    is_from_user = Column(Boolean, default=True, comment="True if from user, False if from bot")
    is_voice_message = Column(Boolean, default=False, comment="Is this a voice message?")
    is_from_business = Column(Boolean, default=False, comment="Is this from Business API?")

    # Business API specific
    business_connection_id = Column(String(255), nullable=True, index=True, comment="Business connection ID")

    # Attachments metadata
    has_attachments = Column(Boolean, default=False, comment="Does message have attachments?")
    attachments_meta = Column(JSON, nullable=True, comment="Metadata about attachments (photo, video, document, etc.)")

    # Bot response metadata
    bot_response_text = Column(Text, nullable=True, comment="Bot's response to this message (if applicable)")
    ai_model_used = Column(String(100), nullable=True, comment="AI model used for response (e.g., 'gpt-4o', 'claude-3-5-sonnet')")

    # Timestamps
    message_date = Column(Integer, nullable=True, comment="Unix timestamp from Telegram")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True, comment="When message was stored in DB")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, comment="When message was last updated")

    # Relationships
    chat = relationship("TelegramChat", back_populates="messages")

    # Indexes for performance
    __table_args__ = (
        Index('idx_chat_message', 'chat_id', 'telegram_message_id'),
        Index('idx_chat_created', 'chat_id', 'created_at'),
        Index('idx_sender_date', 'sender_telegram_id', 'message_date'),
    )

    def __repr__(self):
        return f"<TelegramMessage(id={self.id}, chat_id={self.chat_id}, is_voice={self.is_voice_message})>"
