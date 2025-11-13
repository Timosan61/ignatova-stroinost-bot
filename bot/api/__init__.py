"""
API package for Ignatova-Stroinost bot.

Provides REST endpoints for:
- Message and conversation data (message_endpoints)
- Admin operations like knowledge base loading (admin_endpoints)
"""

from fastapi import APIRouter

# Создаем главный роутер
router = APIRouter()

# Импортируем суб-роутеры
try:
    from bot.api.message_endpoints import router as message_router
    router.include_router(message_router)
except ImportError as e:
    print(f"⚠️ Message endpoints недоступны: {e}")

try:
    from bot.api.admin_endpoints import router as admin_router
    router.include_router(admin_router)
except ImportError as e:
    print(f"⚠️ Admin endpoints недоступны: {e}")

__all__ = ['router']
