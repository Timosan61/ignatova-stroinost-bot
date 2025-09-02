"""
🤖 ignatova-stroinost-bot - Главный сервер

Рефакторированная версия с модульной архитектурой.
Основные возможности:
- Обработка обычных и Business сообщений  
- AI-powered ответы через OpenAI/Anthropic
- Память диалогов через Zep Cloud
- Поддержка голосовых сообщений
- Debug endpoints для мониторинга
"""

import os
import sys
import logging
import asyncio
from datetime import datetime
from fastapi import FastAPI, Request
import telebot

# Добавляем путь для импорта модулей
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Инициализация переменных
AI_ENABLED = False
agent = None
message_handler = None
business_handler = None

print("🚀 Загрузка ignatova-stroinost-bot (Refactored)...")

# Импорт AI модулей
try:
    print("🔄 Загружаем TextilProAgent...")
    from bot.agent import TextilProAgent
    print("🔄 Инициализируем TextilProAgent...")
    agent = TextilProAgent()
    AI_ENABLED = True
    print("✅ AI Agent загружен успешно")
except ImportError as e:
    print(f"⚠️ AI Agent не доступен (ImportError): {e}")
    print(f"⚠️ Детали ImportError: {type(e).__name__}: {str(e)}")
except Exception as e:
    print(f"❌ Ошибка загрузки AI Agent: {e}")
    print(f"❌ Детали ошибки: {type(e).__name__}: {str(e)}")
    import traceback
    print(f"❌ Полный стек ошибок:\n{traceback.format_exc()}")

# Импорт обработчиков
try:
    from bot.handlers.message_handler import MessageHandler
    from bot.handlers.business_handler import BusinessHandler
    print("✅ Обработчики загружены")
except ImportError as e:
    print(f"❌ Ошибка загрузки обработчиков: {e}")

# Настройки
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
WEBHOOK_SECRET_TOKEN = os.getenv("WEBHOOK_SECRET_TOKEN", "QxLZquGScgx1QmwsuUSfJU6HpyTUJoHf2XD4QisrjCk")

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("❌ TELEGRAM_BOT_TOKEN отсутствует!")

print(f"✅ Токен бота получен: {TELEGRAM_BOT_TOKEN[:20]}...")

# Создание бота
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# Инициализация обработчиков
if AI_ENABLED and agent:
    message_handler = MessageHandler(bot, agent)
    business_handler = BusinessHandler(TELEGRAM_BOT_TOKEN, agent)
else:
    message_handler = MessageHandler(bot, None)
    business_handler = BusinessHandler(TELEGRAM_BOT_TOKEN, None)

# Настройка логирования
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/bot.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)
logger.info("🚀 ignatova-stroinost-bot Refactored started")
logger.info(f"🤖 Bot token: {TELEGRAM_BOT_TOKEN[:20]}...")
logger.info(f"🔄 AI Agent enabled: {AI_ENABLED}")

# Создание FastAPI приложения
app = FastAPI(
    title="ignatova-stroinost-bot",
    description="Telegram bot for ignatova-stroinost company",
    version="2.0.0-refactored"
)

# Основные endpoints
@app.get("/")
async def root():
    """Главная страница со статусом бота"""
    return {
        "status": "🟢 ONLINE",
        "service": "ignatova-stroinost-bot Bot Webhook",
        "version": "2.0.0-refactored",
        "bot": "@ignatova_stroinost_bot",
        "bot_id": 7790878041,
        "mode": "WEBHOOK_ONLY",
        "ai_status": "✅ ENABLED" if AI_ENABLED else "❌ DISABLED",
        "openai_configured": bool(agent and agent.openai_client) if AI_ENABLED else False,
        "anthropic_configured": bool(agent and agent.anthropic_client) if AI_ENABLED else False,
        "voice_status": "✅ ENABLED" if AI_ENABLED and agent and hasattr(agent, 'voice_service') else "❌ DISABLED",
        "zep_status": "✅ ENABLED" if AI_ENABLED and agent and agent.zep_client else "❌ DISABLED",
        "endpoints": {
            "webhook_info": "/webhook/info",
            "set_webhook": "/webhook/set",
            "debug_status": "/debug/zep-status",
            "business_owners": "/debug/business-owners",
            "memory_check": "/debug/memory/{session_id}"
        },
        "architecture": "Modular (Refactored)",
        "hint": "Используйте /webhook/set в браузере для установки webhook"
    }

@app.post("/webhook")
async def process_webhook(request: Request):
    """Главный webhook обработчик"""
    try:
        update_dict = await request.json()
        logger.info(f"📨 Получен update: {update_dict.get('update_id', 'unknown')}")
        
        # Обработка Business Connection
        if "business_connection" in update_dict:
            conn_data = update_dict["business_connection"]
            return business_handler.handle_business_connection(conn_data)
        
        # Обработка Business сообщений
        elif "business_message" in update_dict:
            message_data = update_dict["business_message"]
            return await business_handler.handle_business_message(message_data)
        
        # Обработка обычных сообщений
        elif "message" in update_dict:
            message_data = update_dict["message"]
            
            # Голосовые сообщения
            if "voice" in message_data:
                return await message_handler.handle_voice_message(message_data)
            # Текстовые сообщения
            elif "text" in message_data:
                return await message_handler.handle_regular_message(message_data)
            else:
                logger.info("📋 Пропущено сообщение без текста/голоса")
                return {"ok": True, "action": "ignored_non_text_message"}
        
        # Неизвестный тип update
        else:
            logger.info(f"❓ Неизвестный тип update: {list(update_dict.keys())}")
            return {"ok": True, "action": "ignored_unknown_update"}
            
    except Exception as e:
        logger.error(f"❌ Ошибка webhook: {e}")
        return {"ok": False, "error": str(e)}

@app.get("/health")
async def health_check():
    """Проверка здоровья сервиса"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0-refactored",
        "ai_enabled": AI_ENABLED,
        "components": {
            "telegram_bot": bool(bot),
            "ai_agent": bool(agent),
            "message_handler": bool(message_handler),
            "business_handler": bool(business_handler),
            "zep_memory": bool(agent and agent.zep_client) if AI_ENABLED else False
        }
    }

# Webhook управление
@app.get("/webhook/set")
async def set_webhook():
    """Установка webhook"""
    webhook_url = os.getenv('WEBHOOK_URL', 'https://ignatova-stroinost-bot-production.up.railway.app/webhook')
    
    try:
        success = bot.set_webhook(
            url=webhook_url,
            secret_token=WEBHOOK_SECRET_TOKEN,
            allowed_updates=[
                "message", 
                "business_connection", 
                "business_message",
                "edited_business_message", 
                "deleted_business_messages"
            ]
        )
        
        if success:
            logger.info(f"✅ Webhook установлен: {webhook_url}")
            return {
                "status": "success",
                "webhook_url": webhook_url,
                "message": "Webhook успешно установлен"
            }
        else:
            return {
                "status": "error",
                "message": "Не удалось установить webhook"
            }
    except Exception as e:
        logger.error(f"❌ Ошибка установки webhook: {e}")
        return {
            "status": "error",
            "error": str(e)
        }

@app.get("/webhook/info")
async def webhook_info():
    """Информация о webhook"""
    try:
        info = bot.get_webhook_info()
        return {
            "url": info.url,
            "has_custom_certificate": info.has_custom_certificate,
            "pending_update_count": info.pending_update_count,
            "last_error_date": info.last_error_date,
            "last_error_message": info.last_error_message,
            "max_connections": info.max_connections,
            "allowed_updates": info.allowed_updates
        }
    except Exception as e:
        return {"error": str(e)}

# Подключение debug endpoints
try:
    from bot.api.debug_endpoints import create_debug_router
    debug_router = create_debug_router(agent, business_handler)
    app.include_router(debug_router)
    print("✅ Debug endpoints подключены")
except Exception as e:
    print(f"⚠️ Ошибка подключения debug endpoints: {e}")

# Startup события
@app.on_event("startup")
async def startup():
    """События при запуске"""
    logger.info("🎯 FastAPI приложение запущено")
    
    # Автоматическая установка webhook при запуске
    webhook_url = os.getenv('WEBHOOK_URL')
    if webhook_url:
        try:
            success = bot.set_webhook(
                url=f"{webhook_url}/webhook",
                secret_token=WEBHOOK_SECRET_TOKEN,
                allowed_updates=[
                    "message", 
                    "business_connection", 
                    "business_message"
                ]
            )
            if success:
                logger.info(f"✅ Webhook автоматически установлен: {webhook_url}/webhook")
            else:
                logger.warning("⚠️ Не удалось автоматически установить webhook")
        except Exception as e:
            logger.error(f"❌ Ошибка автоустановки webhook: {e}")

@app.on_event("shutdown")
async def shutdown():
    """События при остановке"""
    logger.info("🛑 FastAPI приложение остановлено")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)