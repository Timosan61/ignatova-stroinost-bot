# MySQL Integration - Архив переписок

> Дата создания: 13 ноября 2025
> Статус: Активная (Railway MySQL)

## Обзор

Полная система хранения всех сообщений в MySQL базе данных для долговременной аналитики и архивирования.

**Архитектура адаптирована из:** GPTIFOBIZ project

---

## Что реализовано

### 1. База данных

**Файлы:**
- `bot/database/database.py` - подключение к MySQL с connection pooling
- `bot/database/models.py` - SQLAlchemy модели

**Модели:**

#### TelegramChat
Информация о чатах и пользователях:
- `chat_id` (primary key) - ID чата в Telegram
- `user_name` - имя пользователя
- `first_name`, `last_name` - ФИО
- `username` - Telegram username
- `is_business` - флаг Business API
- `last_message_at` - время последнего сообщения
- `created_at`, `updated_at` - timestamps

#### TelegramMessage
Все сообщения с метаданными:
- `id` (primary key, auto increment)
- `chat_id` (foreign key → TelegramChat)
- `text` - текст сообщения пользователя
- `voice_transcript` - транскрипция голосового сообщения
- `bot_response` - ответ бота
- `ai_model` - модель AI (gpt-4o/claude)
- `is_from_business` - флаг Business API
- `message_metadata` - JSON метаданные (вложения, etc.)
- `created_at` - timestamp

---

### 2. Сервис хранения

**Файл:** `bot/services/message_storage_service.py`

**Возможности:**
- Автоматическое сохранение всех типов сообщений
- Retry логика при database locks (exponential backoff)
- Обработка вложений и голосовых сообщений
- Graceful fallback при недоступности MySQL

**Основные методы:**

#### `save_or_update_chat(chat_data: dict) -> TelegramChat`
Создаёт или обновляет информацию о чате.

```python
chat_record = await message_storage.save_or_update_chat({
    'chat_id': message.chat.id,
    'user_name': message.from_user.first_name,
    'first_name': message.from_user.first_name,
    'last_name': message.from_user.last_name,
    'username': message.from_user.username,
    'is_business': False
})
```

#### `save_message(message_data: dict, chat: TelegramChat) -> TelegramMessage`
Сохраняет сообщение и ответ бота.

```python
await message_storage.save_message({
    'text': text if not was_voice else None,
    'voice_transcript': voice_transcript if was_voice else None,
    'bot_response': response,
    'ai_model': ai_model,
    'is_from_business': False
}, chat=chat_record)
```

**Retry логика:**
```python
# Exponential backoff: 0.5s, 1s, 2s, 4s, 8s
max_retries = 5
retry_delay = 0.5

for attempt in range(max_retries):
    try:
        # Database operation
        break
    except OperationalError as e:
        if "database is locked" in str(e) and attempt < max_retries - 1:
            time.sleep(retry_delay * (2 ** attempt))
        else:
            raise
```

---

### 3. API Endpoints

**Файл:** `bot/api/message_endpoints.py`

REST API для доступа к данным:

#### `GET /api/chats`
Список всех чатов с пагинацией.

**Query параметры:**
- `skip` - offset (default: 0)
- `limit` - количество записей (default: 100, max: 1000)

**Ответ:**
```json
{
  "total": 1523,
  "chats": [
    {
      "chat_id": 123456,
      "user_name": "Анна",
      "first_name": "Анна",
      "username": "anna_user",
      "is_business": false,
      "last_message_at": "2025-11-14T10:30:00",
      "message_count": 45
    }
  ]
}
```

---

#### `GET /api/chats/{chat_id}`
Детальная информация о чате.

**Ответ:**
```json
{
  "chat_id": 123456,
  "user_name": "Анна",
  "first_name": "Анна",
  "last_name": "Иванова",
  "username": "anna_user",
  "is_business": false,
  "last_message_at": "2025-11-14T10:30:00",
  "created_at": "2025-11-01T08:00:00",
  "message_count": 45
}
```

---

#### `GET /api/chats/{chat_id}/messages`
Все сообщения чата.

**Query параметры:**
- `skip` - offset (default: 0)
- `limit` - количество записей (default: 50, max: 500)

**Ответ:**
```json
{
  "total": 45,
  "messages": [
    {
      "id": 789,
      "text": "Привет!",
      "voice_transcript": null,
      "bot_response": "Привет, Анна! Как дела?",
      "ai_model": "gpt-4o-mini",
      "is_from_business": false,
      "created_at": "2025-11-14T10:30:00"
    }
  ]
}
```

---

#### `GET /api/search`
Поиск по тексту сообщений (полнотекстовый поиск).

**Query параметры:**
- `q` - поисковый запрос (обязательный)
- `skip` - offset (default: 0)
- `limit` - количество записей (default: 50, max: 500)

**Ответ:**
```json
{
  "total": 12,
  "messages": [
    {
      "id": 789,
      "chat_id": 123456,
      "text": "Как работать с возражениями?",
      "bot_response": "Используй технику мозгоритмов...",
      "ai_model": "gpt-4o-mini",
      "created_at": "2025-11-14T10:30:00"
    }
  ]
}
```

---

#### `GET /api/stats`
Общая статистика по всем сообщениям.

**Ответ:**
```json
{
  "total_chats": 1523,
  "total_messages": 45823,
  "business_chats": 245,
  "regular_chats": 1278,
  "total_voice_messages": 1234,
  "models_usage": {
    "gpt-4o-mini": 32450,
    "claude-3-5-sonnet": 13373
  }
}
```

---

#### `GET /api/health/db`
Проверка статуса базы данных.

**Ответ (здоровая БД):**
```json
{
  "status": "healthy",
  "database": "mysql",
  "connection": "ok"
}
```

**Ответ (проблемы с БД):**
```json
{
  "status": "unhealthy",
  "database": "mysql",
  "error": "Connection timeout"
}
```

---

### 4. Интеграция

#### Обычные сообщения

**Файл:** `bot/handlers/message_handler.py`

Добавлено сохранение всех обычных сообщений (строки 35-87):

```python
# Сохранение в MySQL
try:
    chat_record = await message_storage.save_or_update_chat({
        'chat_id': message.chat.id,
        'user_name': user_name,
        'first_name': message.from_user.first_name,
        'last_name': message.from_user.last_name,
        'username': message.from_user.username,
        'is_business': False
    })

    await message_storage.save_message({
        'text': text if not was_voice else None,
        'voice_transcript': voice_transcript if was_voice else None,
        'bot_response': response,
        'ai_model': ai_model,
        'is_from_business': False
    }, chat=chat_record)

    logger.info(f"💾 Сообщение сохранено в MySQL (chat_id={message.chat.id})")
except Exception as e:
    logger.warning(f"⚠️ Не удалось сохранить в MySQL: {e}")
    # Бот продолжает работать даже если MySQL недоступен
```

---

#### Business API сообщения

**Файл:** `bot/handlers/business_handler.py`

Полное сохранение Business сообщений (уже было реализовано):

```python
chat_record = await message_storage.save_or_update_chat({
    'chat_id': chat_id,
    'user_name': user_name or first_name,
    'first_name': first_name,
    'username': username,
    'is_business': True
})

await message_storage.save_message({
    'text': text,
    'bot_response': bot_response,
    'ai_model': ai_model,
    'is_from_business': True,
    'message_metadata': {
        'business_connection_id': business_connection_id,
        'message_id': message_id
    }
}, chat=chat_record)
```

---

#### Автоматическая инициализация

**Файл:** `main.py`

База данных автоматически инициализируется при старте бота:

```python
@app.on_event("startup")
async def startup_event():
    """Инициализация при запуске приложения"""
    logger.info("🚀 Starting up...")

    # Инициализация базы данных
    await init_database()
    logger.info("✅ Database initialized")
```

---

## Что сохраняется

| Тип сообщения | Сохраняется | Детали |
|---------------|-------------|--------|
| **Обычные текстовые** | ✅ Да | text + bot_response + ai_model |
| **Business API** | ✅ Да | С фильтрацией владельца + метаданные |
| **Голосовые** | ✅ Да | Транскрипция Whisper + bot_response |
| **Фото/видео/документы** | ✅ Метаданные | JSON в message_metadata |
| **Информация о чатах** | ✅ Да | user_name, first_name, last_name, username |
| **AI модель** | ✅ Да | gpt-4o/gpt-4o-mini/claude-3-5-sonnet |

---

## Гибридный подход памяти

**Разделение ответственности:**

| Система | Назначение | Преимущества |
|---------|-----------|--------------|
| **Zep Cloud** | AI-память и семантический поиск | - Контекст для генерации ответов<br>- Автоматический summary<br>- TTL очистка |
| **MySQL** | Долговременное хранение для аналитики | - SQL запросы<br>- REST API<br>- Неограниченный архив |
| **Graphiti** | База знаний + temporal graph | - Semantic search<br>- Graph traversal<br>- Temporal reasoning |

**Важно:** Системы работают **независимо** - отказ одной не ломает другую.

---

## Railway Configuration

### Environment Variables

```bash
# Автоматически создаётся при добавлении MySQL плагина в Railway
DATABASE_URL=mysql+pymysql://${MYSQL_USER}:${MYSQL_PASSWORD}@${MYSQL_HOST}:${MYSQL_PORT}/${MYSQL_DATABASE}
```

**Компоненты DATABASE_URL:**
- `MYSQL_USER` - пользователь БД
- `MYSQL_PASSWORD` - пароль
- `MYSQL_HOST` - хост (внутренний Railway endpoint)
- `MYSQL_PORT` - порт (обычно 3306)
- `MYSQL_DATABASE` - имя базы данных

### Добавление MySQL в Railway

1. Открой Railway Dashboard: https://railway.app/project/a470438c-3a6c-4952-80df-9e2c067233c6
2. Кликни "+ New Service"
3. Выбери "Database" → "MySQL"
4. Railway автоматически создаст:
   - MySQL сервис
   - Environment variables (DATABASE_URL, MYSQL_*)
   - Internal networking между сервисами

**Service ID:** `d203ed15-2d73-405a-8210-4c100fbaf133`

---

## Graceful Degradation

**Если MySQL недоступен:**
- ✅ Бот продолжает работать
- ✅ Сообщения обрабатываются нормально
- ✅ Ответы генерируются через AI
- ⚠️ Логируется warning: "Не удалось сохранить в MySQL"
- ❌ Сообщения НЕ сохраняются в архив (но бот работает)

**Код (message_handler.py):**
```python
try:
    await message_storage.save_message(...)
    logger.info("💾 Сохранено в MySQL")
except Exception as e:
    logger.warning(f"⚠️ MySQL недоступен: {e}")
    # Бот продолжает работу
```

---

## Мониторинг

### Проверка статуса БД

```bash
curl "https://ignatova-stroinost-bot-production.up.railway.app/api/health/db"
```

### Проверка статистики

```bash
curl "https://ignatova-stroinost-bot-production.up.railway.app/api/stats"
```

### Поиск по сообщениям

```bash
curl "https://ignatova-stroinost-bot-production.up.railway.app/api/search?q=возражения&limit=10"
```

---

## Дополнительная документация

- `docs/MEMORY_ARCHITECTURE.md` - Гибридная архитектура памяти
- `bot/database/models.py` - Схемы SQLAlchemy
- `bot/services/message_storage_service.py` - Реализация сервиса

**Commit:** d0adbd3 - MySQL integration для хранения переписок
