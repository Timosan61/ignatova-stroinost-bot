"""
Database package for Ignatova-Stroinost bot.
Provides MySQL storage for chat conversations and messages.
"""

from bot.database.database import (
    engine,
    SessionLocal,
    Base,
    get_db,
    init_db,
    check_db_connection,
    DATABASE_ENABLED
)

from bot.database.models import TelegramChat, TelegramMessage

__all__ = [
    'engine',
    'SessionLocal',
    'Base',
    'get_db',
    'init_db',
    'check_db_connection',
    'DATABASE_ENABLED',
    'TelegramChat',
    'TelegramMessage',
]
