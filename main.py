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

# Импорт базы данных и API endpoints
try:
    from bot.database import init_db, check_db_connection, DATABASE_ENABLED
    from bot.api import router as api_router
    print(f"✅ База данных: {'ENABLED' if DATABASE_ENABLED else 'DISABLED'}")
    print("✅ API router загружен")
except ImportError as e:
    print(f"⚠️ База данных/API не доступны: {e}")
    DATABASE_ENABLED = False
    api_router = None

# Импорт мониторинга
try:
    from bot.monitoring import get_metrics
    MONITORING_ENABLED = True
    print("✅ Мониторинг embeddings загружен")
except ImportError as e:
    print(f"⚠️ Мониторинг недоступен: {e}")
    MONITORING_ENABLED = False
    get_metrics = None

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

# Регистрация API роутеров
if api_router is not None:
    app.include_router(api_router)
    logger.info("✅ API endpoints зарегистрированы")

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
        "voice_status": "✅ ENABLED" if AI_ENABLED and agent and hasattr(agent, 'voice_service') and agent.voice_service else "❌ DISABLED",
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

@app.post("/api/admin/reload-instruction")
async def reload_instruction_endpoint():
    """Перезагрузка системной инструкции без рестарта сервиса

    Использование: curl -X POST http://localhost:8000/api/admin/reload-instruction
    """
    if not AI_ENABLED or not agent:
        return {
            "status": "error",
            "message": "AI Agent не инициализирован"
        }

    try:
        agent.reload_instruction()
        return {
            "status": "success",
            "message": "Инструкция успешно перезагружена",
            "timestamp": datetime.now().isoformat(),
            "last_updated": agent.instruction.get("last_updated", "unknown")
        }
    except Exception as e:
        logger.error(f"❌ Ошибка перезагрузки инструкции: {e}")
        return {
            "status": "error",
            "message": str(e)
        }

@app.post("/api/admin/migrate-glossary")
async def migrate_glossary():
    """Миграция glossary терминов в Supabase

    Использование: curl -X POST https://...railway.app/api/admin/migrate-glossary
    """
    import time
    from pathlib import Path
    from supabase import create_client
    from openai import OpenAI
    from scripts.parse_knowledge_base import KnowledgeBaseParser

    try:
        # Initialize clients
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        openai_key = os.getenv("OPENAI_API_KEY")

        if not all([supabase_url, supabase_key, openai_key]):
            return {"status": "error", "message": "Missing required environment variables"}

        supabase = create_client(supabase_url, supabase_key)
        openai_client = OpenAI(api_key=openai_key)

        # Parse glossary
        kb_dir = Path("KNOWLEDGE_BASE")
        parser = KnowledgeBaseParser(kb_dir)
        glossary_file = kb_dir / "KNOWLEDGE_BASE_FULL.md"

        glossary_terms = parser.parse_glossary(glossary_file)
        logger.info(f"Found {len(glossary_terms)} glossary terms")

        # Delete existing glossary entries
        try:
            supabase.table("course_knowledge").delete().eq("entity_type", "glossary").execute()
            logger.info("Deleted existing glossary entries")
        except Exception as e:
            logger.warning(f"Could not delete existing entries: {e}")

        # Upload glossary terms
        success_count = 0
        errors = []

        for idx, term in enumerate(glossary_terms):
            try:
                # Generate embedding
                content = f"{term.term}: {term.definition}"
                response = openai_client.embeddings.create(
                    input=content,
                    model="text-embedding-3-small"
                )
                embedding = response.data[0].embedding

                # Prepare row
                row = {
                    "id": f"glossary_{idx}",
                    "entity_type": "glossary",
                    "title": term.term,
                    "content": content,
                    "metadata": {
                        "lesson_number": term.lesson_number,
                        "keywords": term.keywords
                    },
                    "embedding": embedding,
                    "created_at": datetime.now().isoformat()
                }

                # Upsert to Supabase
                supabase.table("course_knowledge").upsert(row).execute()
                success_count += 1

                # Rate limit
                time.sleep(0.05)

            except Exception as e:
                errors.append(f"{term.term}: {str(e)}")
                logger.error(f"Failed to upload term '{term.term}': {e}")

        return {
            "status": "success",
            "total_terms": len(glossary_terms),
            "uploaded": success_count,
            "failed": len(errors),
            "errors": errors[:10] if errors else []
        }

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/api/admin/embedding/stats")
async def get_embedding_stats():
    """Статистика производительности embeddings

    Использование: curl http://localhost:8000/api/admin/embedding/stats
    """
    if not MONITORING_ENABLED or not get_metrics:
        return {
            "status": "unavailable",
            "message": "Мониторинг embeddings не инициализирован"
        }

    try:
        metrics = get_metrics()
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "metrics": metrics.get_summary()
        }
    except Exception as e:
        logger.error(f"❌ Ошибка получения метрик: {e}")
        return {
            "status": "error",
            "message": str(e)
        }

@app.get("/debug/env")
async def debug_env():
    """DEBUG: Проверка переменных окружения"""
    openai_key = os.getenv('OPENAI_API_KEY')
    return {
        "env_vars": {
            "TELEGRAM_BOT_TOKEN": "✅ Set" if os.getenv('TELEGRAM_BOT_TOKEN') else "❌ Missing",
            "OPENAI_API_KEY": "✅ Set" if openai_key else "❌ Missing",
            "OPENAI_API_KEY_LENGTH": len(openai_key) if openai_key else 0,
            "OPENAI_API_KEY_PREFIX": openai_key[:10] if openai_key else "N/A",
            "ANTHROPIC_API_KEY": "✅ Set" if os.getenv('ANTHROPIC_API_KEY') else "❌ Missing",
            "ZEP_API_KEY": "✅ Set" if os.getenv('ZEP_API_KEY') else "❌ Missing",
            "WEBHOOK_SECRET_TOKEN": "✅ Set" if os.getenv('WEBHOOK_SECRET_TOKEN') else "❌ Missing",
            "VOICE_ENABLED": os.getenv('VOICE_ENABLED', 'not_set')
        },
        "ai_enabled": AI_ENABLED,
        "agent_initialized": bool(agent),
        "agent_details": {
            "openai_client_exists": bool(agent and agent.openai_client) if agent else False,
            "anthropic_client_exists": bool(agent and agent.anthropic_client) if agent else False,
            "zep_client_exists": bool(agent and agent.zep_client) if agent else False
        },
        "instruction_file_exists": os.path.exists("data/instruction.json"),
        "voice_service_status": {
            "agent_has_voice_service": bool(agent and hasattr(agent, 'voice_service')),
            "voice_service_initialized": bool(agent and hasattr(agent, 'voice_service') and agent.voice_service),
            "voice_service_type": str(type(agent.voice_service)) if (agent and hasattr(agent, 'voice_service') and agent.voice_service) else None
        }
    }

# Webhook управление
@app.get("/webhook/set")
async def set_webhook():
    """Установка webhook"""
    # Правильный production URL
    webhook_url = "https://ignatova-stroinost-bot-production.up.railway.app/webhook"

    logger.info(f"🔧 Попытка установить webhook: {webhook_url}")

    try:
        # ВАЖНО: не используем secret_token - telegram-bot библиотека не работает с ним
        import requests
        response = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setWebhook",
            json={
                "url": webhook_url,
                "allowed_updates": [
                    "message",
                    "business_connection",
                    "business_message",
                    "edited_business_message",
                    "deleted_business_messages"
                ]
            }
        )
        result = response.json()
        success = result.get("ok", False)

        if success:
            logger.info(f"✅ Webhook установлен: {webhook_url}")
            return {
                "status": "success",
                "webhook_url": webhook_url,
                "message": "Webhook успешно установлен"
            }
        else:
            logger.error(f"❌ Telegram API error: {result}")
            return {
                "status": "error",
                "message": "Не удалось установить webhook",
                "telegram_response": result  # Показываем ответ Telegram API
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
    """
    События при запуске приложения.

    ⚠️ SERVERLESS-OPTIMIZED: Минимальные операции для быстрого cold start
    - Webhook setup перенесён в /api/admin/setup-webhook (вызывать вручную)
    - Только быстрая DB initialization (если включена)
    """
    logger.info("🎯 FastAPI приложение запущено")

    # Detect environment
    is_vercel = os.getenv("VERCEL") == "1" or os.getenv("VERCEL_ENV") is not None
    env_name = "Vercel Serverless" if is_vercel else "Railway/Docker"
    logger.info(f"🌍 Environment: {env_name}")

    # Инициализация базы данных (быстрая операция)
    if DATABASE_ENABLED:
        try:
            logger.info("🔄 Инициализация базы данных...")
            init_db()
            if check_db_connection():
                logger.info("✅ База данных инициализирована и подключена")
            else:
                logger.warning("⚠️ База данных инициализирована, но подключение не проверено")
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации базы данных: {e}")
            logger.warning("   Бот продолжит работу без БД (graceful degradation)")
    else:
        logger.info("⚠️ База данных отключена (DATABASE_URL/POSTGRES_URL не настроен)")

    # 🚫 WEBHOOK SETUP УДАЛЁН ИЗ STARTUP (blocking retry loops)
    # ✅ Используйте POST /api/admin/setup-webhook для установки webhook после deployment
    webhook_url = os.getenv('WEBHOOK_URL')
    if webhook_url:
        logger.info(f"💡 Webhook URL configured: {webhook_url}/webhook")
        logger.info(f"   📍 To activate webhook, call: POST /api/admin/setup-webhook")
    else:
        logger.warning("⚠️ WEBHOOK_URL не настроен. Установите переменную окружения!")

@app.on_event("shutdown")
async def shutdown():
    """События при остановке"""
    logger.info("🛑 FastAPI приложение остановлено")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)