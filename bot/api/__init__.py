"""
API package for Ignatova-Stroinost bot.
Provides REST endpoints for accessing stored conversations.
"""

from bot.api.message_endpoints import router

__all__ = ['router']
