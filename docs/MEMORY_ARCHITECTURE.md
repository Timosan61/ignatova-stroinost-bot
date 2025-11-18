# Архитектура памяти бота

> Дата создания: 14 ноября 2025
> Статус: Активная (гибридная архитектура)

## Обзор

Бот использует **гибридную архитектуру памяти** с тремя системами хранения данных, каждая из которых решает определённые задачи.

---

## Проблема (до оптимизации)

**Три системы памяти работали несогласованно:**

1. **Graphiti (Neo4j)** - только база знаний курса, диалоги НЕ сохранялись
2. **MySQL** - только Business API сообщения, обычные НЕ сохранялись
3. **Zep Cloud** - и диалоги, и legacy база знаний (путаница)

**Дублирование кода:** `bot/agent.py` и `bot/core/memory.py` дублировали функционал Zep

---

## Решение: Гибридная архитектура с чётким разделением

### 🧠 Graphiti (Neo4j) - Единая база знаний + Temporal knowledge graph

**Хранит:**
- ✅ Статическая база знаний курса (449 entities: уроки, FAQ, техники)
- ✅ **НОВОЕ:** Все диалоги пользователей через `add_episode()` - temporal knowledge graph

**Использование:**
- Semantic + Full-text + Graph traversal search
- Поиск по истории диалогов: "что мы обсуждали про X?"
- Temporal reasoning: когда что обсуждалось

**Код:**
```python
# bot/agent.py:561-589
if KNOWLEDGE_SEARCH_AVAILABLE:
    knowledge_service = get_knowledge_search_service()
    if knowledge_service.graphiti_enabled:
        episode_content = f"Пользователь ({user_name}): {user_message}\nАссистент: {bot_response}"
        success, episode_id = await knowledge_service.graphiti_service.add_episode(
            content=episode_content,
            episode_type="conversation",
            metadata={"session_id": session_id, "user_name": user_name},
            source_description=f"Telegram conversation with {user_name}"
        )
```

**Документация:** См. `docs/GRAPHITI_INTEGRATION.md`

---

### 💾 MySQL - Архив всех переписок для аналитики

**Хранит:**
- ✅ **ИСПРАВЛЕНО:** Все обычные сообщения (text + voice) + ответы бота
- ✅ Все Business API сообщения (как было)
- ✅ Метаданные: AI модель, тип сообщения, timestamps

**Использование:**
- REST API endpoints (`/api/chats`, `/api/search`, `/api/stats`)
- SQL запросы для аналитики и отчётов
- Экспорт данных для внешних систем

**Код:**
```python
# bot/handlers/message_handler.py:35-87 (НОВОЕ)
chat_record = await message_storage.save_or_update_chat({...})
await message_storage.save_message({
    'text': text if not was_voice else None,
    'voice_transcript': voice_transcript if was_voice else None,
    'bot_response': response,
    'ai_model': ai_model,
    'is_from_business': False
}, chat=chat_record)
```

**Документация:** См. `docs/MYSQL_INTEGRATION.md`

---

### ☁️ Zep Cloud - Только краткосрочная AI память

**Хранит:**
- ✅ Активные диалоги (последние 6-10 сообщений)
- ✅ Автоматический context summary для AI
- ❌ **УДАЛЕНО:** Legacy база знаний (knowledge_* sessions)

**Использование:**
- Контекст для генерации ответов AI
- Автоматическая очистка старых данных (TTL)

**Что удалено:**
```python
# bot/agent.py:212-328 - удалён весь блок Zep knowledge search
# Больше НЕ используется для базы знаний!
```

---

## Выполненные изменения

### 1. ✅ Исправлено сохранение обычных сообщений в MySQL

**Файл:** `bot/handlers/message_handler.py`

**Изменения:**
- Добавлен импорт `message_storage`
- Добавлено сохранение чата и сообщений (строки 35-87)
- Поддержка голосовых сообщений с транскрипцией
- Graceful fallback при недоступности MySQL

**Результат:** Все диалоги (обычные + Business) теперь в MySQL

---

### 2. ✅ Добавлено сохранение диалогов в Graphiti

**Файл:** `bot/agent.py`

**Изменения:**
- Добавлен вызов `add_episode()` после генерации ответа (строки 561-589)
- Episode формат: "Пользователь: {message}\nАссистент: {response}"
- Метаданные: session_id, user_name, timestamp
- Graceful fallback при недоступности Graphiti

**Результат:** Temporal knowledge graph диалогов для semantic search

---

### 3. ✅ Удалён legacy Zep knowledge search

**Файл:** `bot/agent.py`

**Изменения:**
- Удалён блок "STRATEGY 2: Zep Cloud Search" (было: строки 212-328)
- Обновлён docstring метода `search_knowledge_base()`
- Убрана итерация по `knowledge_{category}_session_{N}`

**Результат:** Единый источник знаний - Graphiti, чистый код

---

### 4. ✅ Рефакторинг дублирования памяти

**Файл:** `bot/core/memory.py`

**Изменения:**
- Переименован в `memory.py.deprecated`
- Функционал полностью в `bot/agent.py`

**Результат:** Один источник истины для работы с Zep

---

## Сравнение ДО/ПОСЛЕ

| Компонент | До оптимизации | После оптимизации |
|-----------|----------------|-------------------|
| **Обычные сообщения в MySQL** | ❌ НЕ сохранялись | ✅ Сохраняются |
| **Диалоги в Graphiti** | ❌ НЕ сохранялись | ✅ Сохраняются (temporal graph) |
| **База знаний** | ⚠️ Graphiti + Zep (дублирование) | ✅ Только Graphiti |
| **Semantic search по диалогам** | ❌ Нет | ✅ Через Graphiti |
| **Дублирование кода** | ⚠️ agent.py + memory.py | ✅ Только agent.py |
| **REST API для аналитики** | ⚠️ Только Business | ✅ Все диалоги |

---

## Архитектурная диаграмма

```
┌─────────────────────────────────────────────────────────────┐
│                     TELEGRAM MESSAGE                        │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
          ┌────────────────┐
          │  Message       │
          │  Handler       │
          └────────┬───────┘
                   │
        ┌──────────┴──────────┐
        │                     │
        ▼                     ▼
┌──────────────┐    ┌──────────────────┐
│   MYSQL      │    │   TextilProAgent │
│   (Archive)  │    │   (AI Logic)     │
└──────────────┘    └─────────┬────────┘
                              │
                    ┌─────────┴─────────┐
                    │                   │
                    ▼                   ▼
          ┌──────────────┐    ┌──────────────┐
          │  GRAPHITI    │    │  ZEP CLOUD   │
          │  (Knowledge) │    │  (Context)   │
          └──────────────┘    └──────────────┘

GRAPHITI: Статика (база знаний) + Диалоги (temporal graph)
ZEP:      Краткосрочная память (last 6-10 messages)
MYSQL:    Долговременный архив (all messages)
```

---

## Преимущества новой архитектуры

### 1. Полное покрытие данных
- Все сообщения сохраняются в MySQL (было: только Business)
- Все диалоги сохраняются в Graphiti (было: только база знаний)

### 2. Semantic search по истории
- "Что мы обсуждали про возражения на прошлой неделе?"
- Temporal reasoning через Graphiti

### 3. REST API для аналитики
- Все диалоги доступны через `/api/chats` (было: только Business)
- SQL запросы для отчётов

### 4. Чистый код
- Один источник истины для Zep (bot/agent.py)
- Удалён legacy Zep knowledge search
- Нет дублирования (memory.py deprecated)

### 5. Graceful degradation
- MySQL недоступен → бот работает (логи warnings)
- Graphiti недоступен → бот работает (логи warnings)
- Zep недоступен → fallback на локальную память

---

## Изменённые файлы

1. `bot/handlers/message_handler.py` (+55 строк) - сохранение в MySQL
2. `bot/agent.py` (+28 строк, -117 строк) - Graphiti episodes + удалён Zep search
3. `bot/core/memory.py` → `memory.py.deprecated` - рефакторинг

**Commit:** `Refactor: Оптимизация архитектуры памяти - гибридный подход`

---

## Дополнительная документация

- `docs/GRAPHITI_INTEGRATION.md` - Graphiti знания и диалоги
- `docs/MYSQL_INTEGRATION.md` - MySQL архив переписок
- `docs/QDRANT_INTEGRATION.md` - Альтернативная система поиска (Qdrant)
