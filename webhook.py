"""
🤖 ignatova-stroinost-bot Bot Webhook Server

Автоматически сгенерированный webhook сервер для ignatova-stroinost-bot.
Основан на Textile Pro Bot с адаптацией под новые требования.

Возможности:
- Обработка обычных сообщений боту
- Обработка Business API сообщений (от вашего Premium аккаунта)
- AI-powered ответы через OpenAI
- Память диалогов через Zep
- Автоматическая установка webhook при старте
"""

import os
import sys
import logging
import traceback
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException
import telebot
import json
import asyncio
import requests

# Добавляем путь для импорта модулей бота
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

print("🚀 Загрузка ignatova-stroinost-bot Bot Webhook Server...")

# Пытаемся импортировать AI agent
try:
    import bot
    print("✅ Модуль bot найден")
    from bot.agent import agent
    print("✅ AI Agent загружен успешно")
    AI_ENABLED = True
except ImportError as e:
    print(f"⚠️ AI Agent не доступен: {e}")
    print(f"📁 Текущая директория: {os.getcwd()}")
    print(f"📁 Файлы в директории: {os.listdir('.')}")
    if os.path.exists('bot'):
        print(f"📁 Файлы в bot/: {os.listdir('bot')}")
    AI_ENABLED = False
except Exception as e:
    print(f"❌ Ошибка загрузки AI Agent: {e}")
    AI_ENABLED = False

# === НАСТРОЙКИ ===
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
WEBHOOK_SECRET_TOKEN = os.getenv("WEBHOOK_SECRET_TOKEN", "QxLZquGScgx1QmwsuUSfJU6HpyTUJoHf2XD4QisrjCk")

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("❌ TELEGRAM_BOT_TOKEN отсутствует!")

print(f"✅ Токен бота получен: {TELEGRAM_BOT_TOKEN[:20]}...")

# === СОЗДАНИЕ СИНХРОННОГО БОТА (НЕ ASYNC!) ===
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# === ЛОГИРОВАНИЕ ===
import logging.handlers

# Создаем директорию для логов если её нет
os.makedirs("logs", exist_ok=True)

# Настраиваем логирование в файл и консоль
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Формат логов
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Файловый хендлер с ротацией
file_handler = logging.handlers.RotatingFileHandler(
    filename="logs/bot.log",
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5,
    encoding='utf-8'
)
file_handler.setFormatter(formatter)
file_handler.setLevel(logging.INFO)

# Консольный хендлер
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
console_handler.setLevel(logging.INFO)

# Добавляем хендлеры к логгеру
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# Логируем запуск приложения
logger.info("🚀 ignatova-stroinost-bot Webhook server started")
logger.info(f"📁 Logs directory: {os.path.abspath('logs')}")
logger.info(f"🤖 Bot token: {TELEGRAM_BOT_TOKEN[:20]}...")
logger.info(f"🔄 AI Agent enabled: {AI_ENABLED}")

# === ИНИЦИАЛИЗАЦИЯ ГОЛОСОВОГО СЕРВИСА ===
voice_service = None
try:
    from bot.voice.voice_service import VoiceService
    from bot.config import OPENAI_API_KEY
    
    if TELEGRAM_BOT_TOKEN and OPENAI_API_KEY:
        voice_service = VoiceService(
            telegram_bot_token=TELEGRAM_BOT_TOKEN,
            openai_api_key=OPENAI_API_KEY
        )
        logger.info("✅ Voice service инициализирован в webhook")
    else:
        logger.warning("⚠️ Voice service не доступен: отсутствуют токены")
except ImportError as e:
    voice_service = None
    logger.warning(f"⚠️ Voice service не доступен: {e}")
except Exception as e:
    voice_service = None
    logger.error(f"❌ Ошибка инициализации Voice service: {e}")

# === ФУНКЦИЯ ДЛЯ ГОЛОСОВОЙ ОБРАБОТКИ ===
async def process_voice_transcription(voice_data: dict, user_id: int) -> dict:
    """Транскрибирует голосовое сообщение (по образцу artem.integrator)"""
    try:
        if not voice_service:
            return {"success": False, "error": "Voice service not available"}
        
        # Правильно извлекаем file_id для разных типов аудио данных
        file_id = voice_data.get('file_id')
        if not file_id:
            # Для обычных аудио сообщений file_id находится внутри audio структуры
            file_id = voice_data.get('audio', {}).get('file_id') if isinstance(voice_data.get('audio'), dict) else None
        
        if not file_id:
            logger.error(f"❌ file_id не найден в voice_data: {voice_data}")
            return {"success": False, "error": "No file_id in voice data"}
        
        logger.info(f"🔑 Извлеченный file_id: {file_id}")
        
        # Используем простой метод транскрибации
        result = await voice_service.transcribe_voice_message(
            voice_data, 
            str(user_id), 
            str(file_id)
        )
        
        return result or {"success": False, "error": "Voice processing failed"}
        
    except Exception as e:
        logger.error(f"❌ Ошибка транскрипции голоса: {e}")
        logger.error(f"📋 voice_data: {voice_data}")
        import traceback
        logger.error(f"📄 Трейс: {traceback.format_exc()}")
        return {"success": False, "error": f"Ошибка транскрипции: {str(e)}"}

# === ФУНКЦИЯ ДЛЯ BUSINESS API ===
def send_business_message(chat_id, text, business_connection_id):
    """
    Отправка сообщения через Business API используя прямой HTTP запрос
    (pyTelegramBotAPI не поддерживает business_connection_id)
    """
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": text,
        "business_connection_id": business_connection_id
    }
    
    try:
        response = requests.post(url, json=data, timeout=10)
        result = response.json()
        
        if result.get("ok"):
            logger.info(f"✅ Business API: сообщение отправлено через HTTP API")
            return result.get("result")
        else:
            logger.error(f"❌ Business API ошибка: {result}")
            return None
    except Exception as e:
        logger.error(f"❌ Business API HTTP ошибка: {e}")
        return None

# === FASTAPI ПРИЛОЖЕНИЕ ===
app = FastAPI(
    title="🤖 ignatova-stroinost-bot Bot", 
    description="Webhook-only режим для ignatova-stroinost-bot бота"
)

# Хранилище последних updates для отладки
from collections import deque
last_updates = deque(maxlen=10)
update_counter = 0

# Хранилище владельцев Business Connection для фильтрации сообщений
business_owners = {}  # {business_connection_id: owner_user_id}

@app.get("/")
async def health_check():
    """Health check endpoint"""
    try:
        bot_info = bot.get_me()
        return {
            "status": "🟢 ONLINE", 
            "service": "ignatova-stroinost-bot Bot Webhook",
            "bot": f"@{bot_info.username}",
            "bot_id": bot_info.id,
            "mode": "WEBHOOK_ONLY",
            "ai_status": "✅ ENABLED" if AI_ENABLED else "❌ DISABLED",
            "openai_configured": bool(os.getenv('OPENAI_API_KEY')),
            "anthropic_configured": bool(os.getenv('ANTHROPIC_API_KEY')),
            "voice_status": "✅ ENABLED" if voice_service else "❌ DISABLED",
            "endpoints": {
                "webhook_info": "/webhook/info",
                "set_webhook": "/webhook/set",
                "delete_webhook": "/webhook (DELETE method)",
                "business_owners": "/debug/business-owners",
                "last_updates": "/debug/last-updates"
            },
            "hint": "Используйте /webhook/set в браузере для установки webhook"
        }
    except Exception as e:
        return {"status": "🔴 ERROR", "error": str(e)}

@app.get("/webhook/set")
async def set_webhook_get():
    """Установка webhook через GET (для браузера)"""
    return await set_webhook()

@app.post("/webhook/set")
async def set_webhook():
    """Установка webhook"""
    try:
        webhook_url = "https://ignatova-stroinost-bot-production.up.railway.app/webhook"
        
        result = bot.set_webhook(
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
        
        if result:
            logger.info(f"✅ Webhook установлен: {webhook_url}")
            return {
                "status": "✅ SUCCESS",
                "webhook_url": webhook_url,
                "secret_token": "✅ Настроен",
                "allowed_updates": "✅ Business API включен"
            }
        else:
            return {"status": "❌ FAILED"}
            
    except Exception as e:
        logger.error(f"❌ Ошибка установки webhook: {e}")
        return {"status": "❌ ERROR", "error": str(e)}

@app.post("/webhook")
async def process_webhook(request: Request):
    """Главный обработчик webhook"""
    global update_counter
    try:
        # Проверяем secret token из заголовков
        secret_token = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
        logger.info(f"📡 Получен secret token: {secret_token}")
        logger.info(f"🔑 Ожидается secret token: {WEBHOOK_SECRET_TOKEN}")
        
        # Проверяем secret token, но не блокируем запросы для отладки
        if secret_token != WEBHOOK_SECRET_TOKEN:
            logger.warning(f"⚠️ Secret token не совпадает: получен='{secret_token}', ожидается='{WEBHOOK_SECRET_TOKEN}'")
            logger.warning("⚠️ ПРОДОЛЖАЕМ обработку для отладки...")
        else:
            logger.info("✅ Secret token корректен")
        
        json_data = await request.body()
        json_string = json_data.decode('utf-8')
        
        logger.info(f"📨 Webhook получен: {json_string[:150]}...")
        print(f"📨 Обработка webhook update...")
        
        update_dict = json.loads(json_string)
        
        # Сохраняем update для отладки
        update_counter += 1
        debug_update = {
            "id": update_counter,
            "timestamp": datetime.now().isoformat(),
            "type": "unknown",
            "data": update_dict
        }
        
        # Определяем тип update
        if "message" in update_dict:
            debug_update["type"] = "message"
        elif "business_message" in update_dict:
            debug_update["type"] = "business_message"
        elif "business_connection" in update_dict:
            debug_update["type"] = "business_connection"
        elif "edited_business_message" in update_dict:
            debug_update["type"] = "edited_business_message"
        elif "deleted_business_messages" in update_dict:
            debug_update["type"] = "deleted_business_messages"
        else:
            debug_update["type"] = f"other: {list(update_dict.keys())}"
            
        last_updates.append(debug_update)
        logger.info(f"📊 Update #{update_counter} тип: {debug_update['type']}")
        
        # === ОБЫЧНЫЕ СООБЩЕНИЯ ===
        if "message" in update_dict:
            msg = update_dict["message"]
            chat_id = msg["chat"]["id"]
            text = msg.get("text", "") or msg.get("caption", "")
            user_id = msg.get("from", {}).get("id", "unknown")
            
            # Диагностическое логирование типов сообщений
            message_types = []
            if msg.get("voice"):
                message_types.append("voice")
            if msg.get("audio"):
                message_types.append("audio")
            if msg.get("document"):
                message_types.append("document")
            if msg.get("text"):
                message_types.append("text")
            if msg.get("video_note"):
                message_types.append("video_note")
            
            logger.info(f"📨 Сообщение от {user_id}: типы={message_types}, voice={bool(msg.get('voice'))}, audio={bool(msg.get('audio'))}")
            user_name = msg.get("from", {}).get("first_name", "Пользователь")
            
            # Проверяем наличие голосового сообщения и аудио
            voice_data = msg.get("voice")
            audio_data = msg.get("audio")
            document_data = msg.get("document")
            is_voice_message = bool(voice_data)
            
            # Базовое логирование без избыточных деталей
            if is_voice_message:
                logger.info(f"🎤 Получено голосовое сообщение от {user_name}")
            elif msg.get("audio"):
                logger.info(f"🎵 Получено аудио сообщение от {user_name}")
            elif text:
                logger.info(f"💬 Получено текстовое сообщение от {user_name}: {text[:50]}...")
            
            try:
                # Пытаемся отправить индикатор набора текста (с защитой от rate limit)
                try:
                    import time
                    time.sleep(0.1)  # Небольшая задержка для избежания rate limit
                    bot.send_chat_action(chat_id, 'typing')
                except Exception as typing_error:
                    logger.warning(f"⚠️ Не удалось отправить typing индикатор: {typing_error}")
                
                # === ОБРАБОТКА ГОЛОСОВЫХ И АУДИО СООБЩЕНИЙ ===
                # По образцу artem.integrator: транскрибируем → устанавливаем text → обрабатываем как текст
                if (is_voice_message or audio_data or (document_data and document_data.get("mime_type", "").startswith("audio/"))):
                    # Определяем какие данные использовать для транскрибации
                    audio_to_process = None
                    audio_type = ""
                    
                    if is_voice_message:
                        audio_to_process = voice_data
                        audio_type = "голосовое"
                    elif audio_data:
                        audio_to_process = audio_data  
                        audio_type = "аудио"
                    elif document_data and document_data.get("mime_type", "").startswith("audio/"):
                        audio_to_process = document_data
                        audio_type = "аудио документ"
                    
                    if audio_to_process and voice_service:
                        try:
                            logger.info(f"🎤 Транскрибируем {audio_type} сообщение от {user_name}")
                            
                            # Транскрибируем голосовое сообщение
                            transcription_result = await process_voice_transcription(audio_to_process, user_id)
                            
                            if transcription_result and transcription_result.get('success'):
                                # Получаем транскрибированный текст
                                transcribed_text = transcription_result.get('text')
                                logger.info(f"✅ Транскрипция: {transcribed_text}")
                                
                                # КЛЮЧЕВОЙ МОМЕНТ: устанавливаем text = транскрипция и обрабатываем как обычное сообщение
                                text = transcribed_text
                                
                                # Продолжаем обработку как текстовое сообщение (ниже)
                            else:
                                # Ошибка транскрипции
                                error_msg = transcription_result.get('error', 'Ошибка транскрипции')
                                logger.error(f"❌ Ошибка транскрипции: {error_msg}")
                                response = "Извините, не удалось обработать ваше голосовое сообщение. Попробуйте отправить текстом или записать еще раз."
                                # Отправляем ошибку и завершаем обработку (с защитой от rate limit)
                                try:
                                    import time
                                    time.sleep(0.2)  # Задержка перед отправкой
                                    bot.send_message(chat_id, response)
                                    logger.info(f"✅ Сообщение об ошибке голоса отправлено в чат {chat_id}")
                                except Exception as send_error:
                                    logger.error(f"❌ Ошибка отправки ответа: {send_error}")
                                return {"ok": True, "action": "voice_transcription_failed"}
                                
                        except Exception as voice_error:
                            logger.error(f"❌ Неожиданная ошибка при обработке голосового сообщения: {voice_error}")
                            response = "Извините, произошла ошибка при обработке голосового сообщения. Попробуйте написать текстом."
                            bot.send_message(chat_id, response)
                            logger.info(f"✅ Сообщение об ошибке голоса отправлено в чат {chat_id}")
                            return {"ok": True, "action": "voice_processing_error"}
                    else:
                        response = "Извините, голосовые сообщения временно не поддерживаются."
                        bot.send_message(chat_id, response)
                        logger.info(f"✅ Сообщение о недоступности голоса отправлено в чат {chat_id}")
                        return {"ok": True, "action": "voice_service_unavailable"}
                
                # === ОБРАБОТКА КОМАНД И ТЕКСТА ===
                # Инициализируем response для предотвращения ошибок
                response = None
                
                if text.startswith("/start"):
                    if AI_ENABLED:
                        response = agent.get_welcome_message()
                    else:
                        response = f"👋 Привет, {user_name}! Добро пожаловать в ignatova-stroinost-bot бот!"
                
                elif text.startswith("/voice_debug"):
                    # Команда для получения последних ошибок голосового сервиса
                    if voice_service:
                        # Создаем тестовое голосовое сообщение с валидной структурой
                        test_voice = {
                            'file_id': 'test_invalid_file_id_12345',
                            'duration': 3,
                            'file_size': 1000
                        }
                        
                        try:
                            result = await process_voice_transcription(test_voice, user_id)
                            
                            response = f"""🔍 Тест голосового сервиса:
                            
📊 **Результат тестирования:**
• Успех: {result.get('success', False)}
• Ошибка: {result.get('error', 'Нет ошибки')}

💡 **Диагностика:**
Если success=False, то проблема в обработке файлов.
Если success=True, то проблема в webhook логике."""
                        except Exception as e:
                            response = f"❌ Ошибка при тестировании: {str(e)}"
                    else:
                        response = "❌ Голосовой сервис недоступен"
                
                elif text.startswith("/voice_test"):
                    # Тестовая команда для проверки голосового сервиса
                    if voice_service:
                        service_info = voice_service.get_service_info()
                        test_results = await voice_service.test_service()
                        
                        response = f"""🎤 Статус голосового сервиса:
                        
📊 **Общая информация:**
• Сервис: {service_info['service_name']}
• Статус: {service_info['status']}
• Язык: {service_info['default_language']}
• Макс. длительность: {service_info['max_duration']}с

🔧 **Компоненты:**
• Telegram: {"✅" if test_results['telegram_token'] else "❌"}
• OpenAI: {"✅" if test_results['openai_key'] else "❌"}
• Whisper: {"✅" if test_results['whisper_client'] else "❌"}
• Подключение: {"✅" if test_results['whisper_connection'] else "❌"}

🎯 **Готовность:** {"✅ Готов" if test_results['service_ready'] else "❌ Не готов"}

📝 **Поддерживаемые форматы:** {', '.join(service_info['supported_formats'][:5])}"""
                    else:
                        response = "❌ Голосовой сервис недоступен"
                
                elif text.startswith("/help"):
                    voice_status = "✅ Поддерживаются" if voice_service else "❌ Не поддерживаются"
                    response = f"""ℹ️ Помощь по ignatova-stroinost-bot:
/start - начать работу
/help - показать помощь
/voice_test - проверить голосовой сервис

📝 Текстовые сообщения: ✅ Поддерживаются
🎤 Голосовые сообщения: {voice_status}

Просто напишите ваш вопрос или отправьте голосовое сообщение!"""
                
                # Если есть текст - обрабатываем через AI
                elif text and AI_ENABLED:
                    try:
                        session_id = f"user_{user_id}"
                        # Создаем пользователя в Zep если нужно
                        if agent.zep_client:
                            await agent.ensure_user_exists(f"user_{user_id}", {
                                'first_name': user_name,
                                'email': f'{user_id}@telegram.user'
                            })
                            await agent.ensure_session_exists(session_id, f"user_{user_id}")
                        response = await agent.generate_response(text, session_id, user_name)
                        
                    except Exception as ai_error:
                        logger.error(f"Ошибка AI генерации: {ai_error}")
                        response = f"Извините, произошла техническая ошибка. Попробуйте позже или напишите вопрос снова."
                    
                elif text:
                    # Fallback если AI не доступен
                    response = f"👋 {user_name}, получил ваш вопрос! Подготовлю ответ. Минуточку!"
                else:
                    return {"ok": True, "action": "no_action"}
                    
                # Отправляем ответ (с проверкой на None)
                if response:
                    bot.send_message(chat_id, response)
                    logger.info(f"✅ Ответ отправлен в чат {chat_id}")
                    print(f"✅ Отправлен ответ пользователю {user_name}")
                else:
                    logger.warning(f"⚠️ Response не установлен для сообщения: {text[:50]}")
                    return {"ok": True, "action": "no_response_generated"}
                
            except Exception as e:
                logger.error(f"Ошибка обработки сообщения: {e}")
                bot.send_message(chat_id, "Извините, произошла непредвиденная ошибка. Попробуйте написать снова.")
        
        # === BUSINESS СООБЩЕНИЯ ===
        elif "business_message" in update_dict:
            bus_msg = update_dict["business_message"]
            
            chat_id = bus_msg["chat"]["id"]
            text = bus_msg.get("text", "") or bus_msg.get("caption", "")
            user_id = bus_msg.get("from", {}).get("id", "unknown")
            business_connection_id = bus_msg.get("business_connection_id")
            user_name = bus_msg.get("from", {}).get("first_name", "Клиент")
            
            # Проверяем наличие голосового сообщения в Business API
            voice_data = bus_msg.get("voice")
            is_voice_message = bool(voice_data)
            
            # Отладочное логирование для Business API
            if is_voice_message:
                logger.info(f"🎤 Business: Получены данные голосового сообщения: {voice_data}")
            
            # Проверим также другие типы аудио в Business API
            audio_data = bus_msg.get("audio")
            document_data = bus_msg.get("document")
            if audio_data:
                logger.info(f"🎵 Business: Получено аудио сообщение: {audio_data}")
            if document_data and document_data.get("mime_type", "").startswith("audio/"):
                logger.info(f"📎 Business: Получен аудио документ: {document_data}")
            
            # 🚫 КРИТИЧНАЯ ПРОВЕРКА: Игнорируем сообщения от владельца аккаунта
            if business_connection_id and business_connection_id in business_owners:
                owner_id = business_owners[business_connection_id]
                if str(user_id) == str(owner_id):
                    logger.info(f"🚫 ИГНОРИРУЕМ сообщение от владельца аккаунта: {user_name} (ID: {user_id})")
                    return {"ok": True, "action": "ignored_owner_message", "reason": "message_from_business_owner"}
            
            # Обрабатываем business сообщения (голосовые и текстовые)
            if text or is_voice_message:
                try:
                    logger.info(f"🔄 Начинаю обработку business message: {'voice' if is_voice_message else 'text'}, chat_id={chat_id}")
                    
                    if AI_ENABLED:
                        logger.info(f"🤖 AI включен, генерирую ответ...")
                        session_id = f"business_{user_id}"
                        
                        # Создаем пользователя в Zep если нужно
                        if agent.zep_client:
                            await agent.ensure_user_exists(f"business_{user_id}", {
                                'first_name': user_name,
                                'email': f'{user_id}@business.telegram.user'
                            })
                            await agent.ensure_session_exists(session_id, f"business_{user_id}")
                        
                        # === ОБРАБОТКА ГОЛОСОВЫХ И АУДИО BUSINESS СООБЩЕНИЙ ===
                        # По образцу artem.integrator: транскрибируем → устанавливаем text → обрабатываем как текст
                        if (is_voice_message or audio_data or (document_data and document_data.get("mime_type", "").startswith("audio/"))):
                            # Определяем какие данные использовать для транскрибации
                            audio_to_process = None
                            audio_type = ""
                            
                            if is_voice_message:
                                audio_to_process = voice_data
                                audio_type = "голосовое business"
                            elif audio_data:
                                audio_to_process = audio_data
                                audio_type = "аудио business"
                            elif document_data and document_data.get("mime_type", "").startswith("audio/"):
                                audio_to_process = document_data
                                audio_type = "аудио документ business"
                            
                            if audio_to_process and voice_service:
                                try:
                                    logger.info(f"🎤 Транскрибируем {audio_type} сообщение от {user_name}")
                                    
                                    # Транскрибируем голосовое сообщение
                                    transcription_result = await process_voice_transcription(audio_to_process, user_id)
                                    
                                    if transcription_result and transcription_result.get('success'):
                                        # Получаем транскрибированный текст
                                        transcribed_text = transcription_result.get('text')
                                        logger.info(f"✅ Business транскрипция: {transcribed_text}")
                                        
                                        # КЛЮЧЕВОЙ МОМЕНТ: устанавливаем text = транскрипция и обрабатываем как обычное сообщение
                                        text = transcribed_text
                                        
                                        # Продолжаем обработку как текстовое сообщение (ниже в блоке AI)
                                    else:
                                        # Ошибка транскрипции
                                        error_msg = transcription_result.get('error', 'Ошибка транскрипции')
                                        logger.error(f"❌ Ошибка business транскрипции: {error_msg}")
                                        response = "Извините, не удалось обработать ваше голосовое сообщение. Попробуйте отправить текстом."
                                        
                                except Exception as voice_error:
                                    logger.error(f"❌ Ошибка при обработке business голосового сообщения: {voice_error}")
                                    response = "Извините, произошла ошибка при обработке голосового сообщения. Попробуйте написать текстом."
                            else:
                                response = "Извините, голосовые сообщения временно не поддерживаются."
                        
                        # === ОБРАБОТКА ТЕКСТОВЫХ BUSINESS СООБЩЕНИЙ (включая транскрибированные) ===
                        if text:  # Обрабатываем текст (в том числе транскрибированный из голоса)
                            response = await agent.generate_response(text, session_id, user_name)
                            logger.info(f"✅ AI ответ сгенерирован: {response[:100]}...")
                    else:
                        logger.info(f"🤖 AI отключен, использую стандартный ответ")
                        if is_voice_message:
                            response = f"👋 Здравствуйте, {user_name}! Получил ваше голосовое сообщение, но обработка голоса временно недоступна. Попробуйте написать текстом."
                        else:
                            response = f"👋 Здравствуйте, {user_name}! Получил ваш вопрос. Подготовлю ответ!"
                    
                    # Для business_message используем специальную функцию
                    logger.info(f"📤 Пытаюсь отправить ответ клиенту {user_name}...")
                    if business_connection_id:
                        result = send_business_message(chat_id, response, business_connection_id)
                        if result:
                            logger.info(f"✅ Business ответ отправлен клиенту в чат {chat_id}")
                        else:
                            logger.error(f"❌ Не удалось отправить через Business API")
                    else:
                        bot.send_message(chat_id, response)
                        logger.warning(f"⚠️ Отправлено как обычное сообщение (fallback)")
                    
                    print(f"✅ Business ответ отправлен клиенту {user_name}")
                    
                except Exception as e:
                    logger.error(f"❌ Ошибка обработки business сообщения: {e}")
                    logger.error(f"Traceback:\n{traceback.format_exc()}")
                    
                    # ВАЖНО: Отправляем ошибку ТОЖЕ через Business API!
                    try:
                        error_message = "Извините, произошла техническая ошибка. Попробуйте написать снова."
                        
                        if business_connection_id:
                            result = send_business_message(chat_id, error_message, business_connection_id)
                            if result:
                                logger.info(f"✅ Сообщение об ошибке отправлено через Business API")
                            else:
                                bot.send_message(chat_id, error_message)
                                logger.warning(f"⚠️ Business API не сработал, отправлено обычным способом")
                        else:
                            bot.send_message(chat_id, error_message)
                            logger.warning(f"⚠️ Сообщение об ошибке отправлено БЕЗ Business API (нет connection_id)")
                            
                    except Exception as send_error:
                        logger.error(f"❌ Не удалось отправить сообщение об ошибке: {send_error}")
        
        # === BUSINESS CONNECTION ===
        elif "business_connection" in update_dict:
            conn = update_dict["business_connection"]
            is_enabled = conn.get("is_enabled", False)
            connection_id = conn.get("id")
            user_info = conn.get("user", {})
            user_name = user_info.get("first_name", "Пользователь")
            owner_user_id = user_info.get("id")
            
            # Сохраняем владельца Business Connection для фильтрации сообщений
            if connection_id and owner_user_id:
                if is_enabled:
                    business_owners[connection_id] = owner_user_id
                    logger.info(f"✅ Сохранен владелец Business Connection: {user_name} (ID: {owner_user_id}) для connection_id: {connection_id}")
                else:
                    business_owners.pop(connection_id, None)
                    logger.info(f"❌ Удален владелец Business Connection: {user_name} (connection_id: {connection_id})")
            
            status = "✅ Подключен" if is_enabled else "❌ Отключен"
            logger.info(f"{status} к Business аккаунту: {user_name}")
            logger.info(f"📊 Всего активных Business Connection: {len(business_owners)}")
        
        return {"ok": True, "status": "processed", "update_id": update_counter}
        
    except Exception as e:
        logger.error(f"❌ Ошибка webhook: {e}")
        return {"ok": False, "error": str(e)}

@app.get("/debug/logs")
async def get_recent_logs():
    """Получить последние логи для отладки"""
    try:
        import os
        log_file = "logs/bot.log"
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                # Возвращаем последние 20 строк
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

@app.get("/debug/zep-status") 
async def get_zep_status():
    """Проверить статус Zep Memory"""
    if not AI_ENABLED:
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

@app.get("/debug/voice-logs")
async def get_voice_logs():
    """Получить последние логи связанные с голосовыми сообщениями"""
    try:
        import os
        log_file = "logs/bot.log"
        voice_lines = []
        
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                # Ищем логи связанные с голосом
                voice_keywords = ['голос', 'voice', '🎤', '🔑', 'file_id', 'транскри', 'whisper', 'audio']
                for line in lines:
                    if any(keyword.lower() in line.lower() for keyword in voice_keywords):
                        voice_lines.append(line.strip())
                
                # Возвращаем последние 30 записей о голосе
                recent_voice_lines = voice_lines[-30:] if len(voice_lines) > 30 else voice_lines
                
                return {
                    "status": "success",
                    "voice_logs": recent_voice_lines,
                    "total_voice_logs": len(voice_lines),
                    "voice_service_status": "active" if voice_service else "inactive"
                }
        else:
            return {
                "status": "error",
                "error": "Log file not found"
            }
    except Exception as e:
        return {"status": "error", "error": str(e)}

@app.get("/debug/production-status")
async def production_status():
    """Получить подробный статус продакшен сервера"""
    try:
        import os
        import sys
        from datetime import datetime
        
        # Безопасная проверка OpenAI ключа
        openai_key_info = {
            "exists": bool(OPENAI_API_KEY),
            "length": len(OPENAI_API_KEY) if OPENAI_API_KEY else 0,
            "starts_with": OPENAI_API_KEY[:10] + "..." if OPENAI_API_KEY and len(OPENAI_API_KEY) > 10 else "None",
            "format_check": OPENAI_API_KEY.startswith("sk-") if OPENAI_API_KEY else False
        }
        
        status = {
            "timestamp": datetime.now().isoformat(),
            "voice_service": {
                "initialized": voice_service is not None,
                "telegram_token": bool(TELEGRAM_BOT_TOKEN),
                "openai_key": bool(OPENAI_API_KEY),
                "openai_key_details": openai_key_info
            },
            "ai_agent": {
                "enabled": AI_ENABLED,
                "initialized": agent is not None
            },
            "environment": {
                "python_version": sys.version,
                "working_directory": os.getcwd(),
                "log_file_exists": os.path.exists("logs/bot.log")
            },
            "recent_errors": []
        }
        
        # Получаем последние ошибки из логов
        if os.path.exists("logs/bot.log"):
            with open("logs/bot.log", 'r', encoding='utf-8') as f:
                lines = f.readlines()
                error_lines = []
                for line in lines[-50:]:  # Последние 50 строк
                    if 'ERROR' in line or '❌' in line or 'Exception' in line:
                        error_lines.append(line.strip())
                status["recent_errors"] = error_lines[-10:]  # Последние 10 ошибок
        
        return {"status": "success", "data": status}
        
    except Exception as e:
        return {"status": "error", "error": str(e)}

@app.get("/debug/test-openai")
async def test_openai():
    """Протестировать подключение к OpenAI API"""
    try:
        from datetime import datetime
        
        if not OPENAI_API_KEY:
            return {"status": "error", "error": "OpenAI API key not provided"}
        
        import openai
        
        # Тестируем подключение к OpenAI API
        try:
            client = openai.OpenAI(api_key=OPENAI_API_KEY)
            
            # Простой тест API - список моделей
            models = client.models.list()
            
            # Проверяем доступность Whisper
            whisper_available = any("whisper" in model.id for model in models.data)
            
            return {
                "status": "success",
                "api_key_valid": True,
                "whisper_available": whisper_available,
                "total_models": len(models.data),
                "test_timestamp": datetime.now().isoformat()
            }
            
        except openai.AuthenticationError:
            return {
                "status": "error", 
                "error": "Authentication failed - invalid API key",
                "api_key_valid": False
            }
        except openai.APIError as e:
            return {
                "status": "error",
                "error": f"OpenAI API error: {str(e)}",
                "api_key_valid": "unknown"
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Connection error: {str(e)}",
                "api_key_valid": "unknown"
            }
            
    except Exception as e:
        return {"status": "error", "error": str(e)}

@app.get("/debug/webhook-info")
async def webhook_info():
    """Получить информацию о настройке webhook"""
    try:
        import requests
        
        # Получаем информацию о webhook
        webhook_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getWebhookInfo"
        response = requests.get(webhook_url)
        webhook_data = response.json()
        
        # Проверяем какие типы обновлений разрешены
        allowed_updates = webhook_data.get("result", {}).get("allowed_updates", [])
        
        return {
            "status": "success",
            "webhook_info": webhook_data.get("result", {}),
            "voice_allowed": "message" in allowed_updates or len(allowed_updates) == 0,
            "all_allowed_updates": allowed_updates,
            "voice_processing_enabled": voice_service is not None
        }
        
    except Exception as e:
        return {"status": "error", "error": str(e)}

@app.get("/debug/prompt")
async def get_current_prompt():
    """Получить информацию о текущих инструкциях"""
    try:
        if AI_ENABLED and agent:
            instruction = agent.instruction
            return {
                "status": "success",
                "last_updated": instruction.get("last_updated", "неизвестно"),
                "system_instruction_length": len(instruction.get("system_instruction", "")),
                "welcome_message": instruction.get("welcome_message", ""),
                "ai_enabled": True
            }
        else:
            return {
                "status": "error",
                "error": "AI Agent не инициализирован",
                "ai_enabled": False
            }
    except Exception as e:
        logger.error(f"❌ Ошибка получения промпта: {e}")
        return {"status": "error", "error": str(e)}

@app.post("/admin/reload-instructions")
async def reload_instructions():
    """Перезагрузить инструкции из файла"""
    try:
        if AI_ENABLED and agent:
            old_updated = agent.instruction.get('last_updated', 'неизвестно')
            agent.reload_instruction()
            new_updated = agent.instruction.get('last_updated', 'неизвестно')
            
            changed = old_updated != new_updated
            
            return {
                "status": "success",
                "changed": changed,
                "old_updated": old_updated,
                "new_updated": new_updated,
                "message": "Инструкции обновлены" if changed else "Инструкции перезагружены (без изменений)"
            }
        else:
            return {
                "status": "error",
                "error": "AI Agent не инициализирован"
            }
    except Exception as e:
        logger.error(f"❌ Ошибка перезагрузки промпта: {e}")
        return {"status": "error", "error": str(e)}

@app.post("/admin/update-instructions")
async def update_instructions(request: Request):
    """Обновить инструкции напрямую через API"""
    try:
        if not AI_ENABLED or not agent:
            return {
                "status": "error",
                "error": "AI Agent не инициализирован"
            }
        
        # Получаем данные из запроса
        instruction_data = await request.json()
        
        # Проверяем обязательные поля
        required_fields = ["system_instruction", "welcome_message", "settings"]
        for field in required_fields:
            if field not in instruction_data:
                return {
                    "status": "error",
                    "error": f"Отсутствует обязательное поле: {field}"
                }
        
        # Добавляем время обновления
        instruction_data["last_updated"] = datetime.now().isoformat()
        
        # Сохраняем в файл
        import json
        from bot.config import INSTRUCTION_FILE
        with open(INSTRUCTION_FILE, 'w', encoding='utf-8') as f:
            json.dump(instruction_data, f, ensure_ascii=False, indent=2)
        
        # Принудительно перезагружаем в агенте
        old_updated = agent.instruction.get('last_updated', 'неизвестно')
        
        # Принудительно очищаем кеш и перезагружаем
        agent.instruction = agent._load_instruction()
        
        new_updated = agent.instruction.get('last_updated', 'неизвестно')
        
        logger.info(f"✅ Инструкции обновлены через API: {old_updated} -> {new_updated}")
        
        return {
            "status": "success",
            "changed": True,
            "old_updated": old_updated,
            "new_updated": new_updated,
            "message": "Инструкции успешно обновлены через API"
        }
        
    except Exception as e:
        logger.error(f"❌ Ошибка обновления инструкций через API: {e}")
        return {"status": "error", "error": str(e)}

@app.get("/admin/get-instructions")
async def get_current_instructions():
    """Получить текущие инструкции из бота"""
    try:
        if not AI_ENABLED or not agent:
            return {
                "status": "error",
                "error": "AI Agent не инициализирован"
            }
        
        return {
            "status": "success",
            "instructions": agent.instruction,
            "loaded_at": agent.instruction.get('last_updated', 'неизвестно')
        }
        
    except Exception as e:
        logger.error(f"❌ Ошибка получения инструкций: {e}")
        return {"status": "error", "error": str(e)}

@app.post("/admin/test-response")
async def test_bot_response(request: Request):
    """Тестовый ответ бота для проверки актуальности инструкций"""
    try:
        if not AI_ENABLED or not agent:
            return {
                "status": "error",
                "error": "AI Agent не инициализирован"
            }
        
        # Получаем тестовое сообщение из запроса
        data = await request.json()
        test_message = data.get("message", "Представьтесь, пожалуйста")
        
        # Генерируем ответ
        response = await agent.generate_response(
            user_message=test_message,
            session_id="test_admin_session",
            user_name="Admin"
        )
        
        return {
            "status": "success",
            "test_message": test_message,
            "bot_response": response,
            "system_instruction_used": agent.instruction.get("system_instruction", "")[:200] + "...",
            "instruction_timestamp": agent.instruction.get("last_updated", "неизвестно")
        }
        
    except Exception as e:
        logger.error(f"❌ Ошибка тестового ответа: {e}")
        return {"status": "error", "error": str(e)}

@app.on_event("startup")
async def startup():
    """Запуск сервера"""
    print("\n" + "="*50)
    print("🚀 ignatova-stroinost-bot BOT WEBHOOK SERVER")
    print("="*50)
    
    # Очищаем webhook при старте
    try:
        bot.delete_webhook()
        print("🧹 Webhook очищен")
    except:
        pass
    
    try:
        bot_info = bot.get_me()
        print(f"🤖 Бот: @{bot_info.username}")
        print(f"📊 ID: {bot_info.id}")
        print(f"📛 Имя: {bot_info.first_name}")
        print("🔗 Режим: WEBHOOK ONLY")
        print("❌ Polling: ОТКЛЮЧЕН")
        print(f"🤖 AI: {'✅ ВКЛЮЧЕН' if AI_ENABLED else '❌ ОТКЛЮЧЕН'}")
        print(f"🔑 OpenAI API: {'✅ Настроен' if os.getenv('OPENAI_API_KEY') else '❌ Не настроен'}")
        print("="*50)
        logger.info("✅ Бот инициализирован успешно")
        
        # ВСЕГДА автоматически устанавливаем webhook при старте
        print("🔧 Автоматическая установка webhook...")
        try:
            # Используем правильный URL вместо переменной окружения
            webhook_url = "https://ignatova-stroinost-bot-production.up.railway.app/webhook"
            result = bot.set_webhook(
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
            
            if result:
                print(f"✅ Webhook автоматически установлен: {webhook_url}")
                logger.info(f"✅ Webhook установлен при старте: {webhook_url}")
            else:
                print("❌ Не удалось установить webhook автоматически")
                logger.error("Ошибка автоматической установки webhook")
                
        except Exception as e:
            print(f"❌ Ошибка при автоматической установке webhook: {e}")
            logger.error(f"Ошибка автоустановки webhook: {e}")
            
    except Exception as e:
        print(f"❌ Ошибка инициализации: {e}")
        logger.error(f"❌ Ошибка инициализации бота: {e}")

@app.on_event("shutdown")
async def shutdown():
    """Остановка сервера"""
    logger.info("🛑 Остановка ignatova-stroinost-bot Bot Webhook Server")
    print("🛑 Сервер остановлен")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    print(f"🌐 Запуск на порту {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)