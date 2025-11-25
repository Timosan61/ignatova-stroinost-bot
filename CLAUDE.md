# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Язык общения
**ОБЯЗАТЕЛЬНОЕ ПРАВИЛО:** Всегда отвечай на русском языке во всех взаимодействиях с пользователем.

---

## Архитектура проекта

Telegram бот с AI-агентом для курса "Всепрощающая" Натальи Игнатовой. Модульная архитектура с гибридной системой памяти и векторным поиском.

### Точка входа
- **Production:** `main.py` (FastAPI + Telegram webhook)
- **Local dev:** `uvicorn main:app --reload` или `python main.py`

### Основные компоненты

```
bot/
├── agent.py              # TextilProAgent - основная AI логика
├── config.py             # Конфигурация (env vars, feature flags)
├── handlers/             # Обработчики сообщений
│   ├── message_handler.py    # Обычные сообщения
│   └── business_handler.py   # Business API + фильтрация владельца
├── services/             # Внешние сервисы
│   ├── knowledge_search.py   # Гибридный поиск (Qdrant/Supabase/Graphiti)
│   ├── qdrant_service.py     # Vector DB (3,234 entities)
│   ├── supabase_service.py   # PostgreSQL + pgvector
│   └── graphiti_service.py   # Knowledge graph (deprecated)
├── voice/                # Голосовые сообщения
│   └── voice_service.py      # Whisper API транскрипция
└── database/             # MySQL архив
    └── database.py
```

### Системы памяти и поиска

| Система | Назначение | Статус | Документация |
|---------|-----------|--------|--------------|
| **Qdrant** | Векторный поиск по базе знаний (384D, 3,234 entities) | ✅ Production | `docs/QDRANT_INTEGRATION.md` |
| **Supabase** | Alternative vector store (1536D OpenAI embeddings) | ✅ Ready | `docs/SUPABASE_INTEGRATION.md` |
| **Zep Cloud** | Краткосрочная память диалогов (context + history) | ✅ Active | Built-in |
| **MySQL** | Долговременный архив всех сообщений | ✅ Active | `docs/MYSQL_INTEGRATION.md` |
| **Graphiti** | Knowledge graph (Neo4j/FalkorDB) | ⚠️ Standby | `docs/GRAPHITI_INTEGRATION.md` |

**Ключевое различие:**
- **Qdrant/Supabase**: База знаний курса (FAQ, уроки, корректировки)
- **Zep**: Контекст текущей беседы пользователя
- **MySQL**: Архив для аналитики

**Supabase:**
- Project ID: `qqppsflwztnxcegcbwqd`
- URL: `https://qqppsflwztnxcegcbwqd.supabase.co`
- Table: `course_knowledge`
- Entities: **3,234** (FAQ: 25, Lessons: 127, Corrections: 275, Questions: 2,635, Brainwrites: 172)
- Embedding model: `text-embedding-3-small` (1536D vectors)

---

## 🔧 MCP Supabase (РЕКОМЕНДУЕТСЯ)

**Используй MCP Supabase для работы с базой данных:**

```bash
# Проверить таблицы
mcp__supabase__list_tables(project_id="qqppsflwztnxcegcbwqd")

# Статистика по entity_type
mcp__supabase__execute_sql(
    project_id="qqppsflwztnxcegcbwqd",
    query="SELECT entity_type, COUNT(*) FROM course_knowledge GROUP BY entity_type"
)

# Поиск данных
mcp__supabase__execute_sql(
    project_id="qqppsflwztnxcegcbwqd",
    query="SELECT * FROM course_knowledge WHERE content ILIKE '%термин%' LIMIT 5"
)
```

**Преимущества MCP Supabase:**
- Прямой доступ к базе без локальных credentials
- Быстрая диагностика данных
- Миграции через SQL

---

## КРИТИЧЕСКИ ВАЖНЫЕ ПРАВИЛА

### 1. Git и Deployment Workflow

**ВСЕГДА после изменений в коде:**
```bash
git add .
git commit -m "Описание изменений"
git push origin main
```

**ОБЯЗАТЕЛЬНО через 90 секунд после push:**
```bash
# Проверка статуса деплоя
python3 scripts/railway_monitor.py info

# Непрерывный мониторинг (рекомендуется)
python3 scripts/railway_monitor.py monitor
```

Railway автоматически деплоит при push на main. Мониторинг критичен для раннего обнаружения ошибок.

### 2. Multi-Stage Search Architecture

**Приоритеты источников** (файл: `bot/services/knowledge_search.py`):

1. **Lessons** (методология курса) - BOOST 1.5x
2. **Corrections** (стиль куратора) - BOOST 1.2x
3. **FAQ** (частые вопросы) - BOOST 1.0x
4. **Questions/Brainwrites** - ИСКЛЮЧЕНЫ из search results

**Проблема:** Brainwrites (примеры студентов) содержат ошибки и НЕ должны попадать в ответы бота.

**Решение:** Entity type filtering в `_search_semantic()` и `_search_hybrid()`:
```python
# ЭТАП 1: Поиск в уроках
lesson_results = await qdrant.search_semantic(query, entity_type="lesson")
# ЭТАП 2: Поиск в корректировках
correction_results = await qdrant.search_semantic(query, entity_type="correction")
# ЭТАП 3: FAQ (fallback)
faq_results = await qdrant.search_semantic(query, entity_type="faq")
```

### 3. Knowledge Base Migration (Qdrant)

**Текущий статус:** 3,234 entities загружено (100% complete)
- FAQ: 25
- Lessons: 127
- Corrections: 275
- Questions: 2,635 ✅ (было 0, исправлен баг в `parse_questions()`)
- Brainwrites: 172

**Миграция:**
```bash
# Локальная миграция (рекомендуется - не блокирует бот)
python3 scripts/migrate_to_qdrant.py

# Проверка статуса
curl "https://ignatova-stroinost-bot-production.up.railway.app/api/admin/qdrant/stats"
```

**Баг исправлен** (commit: в этой сессии):
- `scripts/parse_knowledge_base.py:373-378` - TypeError при `sample_limit=None`
- Решение: добавлена проверка `if sample_limit is None`

### 4. FalkorDB Imports Issue

**Проблема:** ImportError cascade блокирует AI agent при загрузке.

**Решение:** FalkorDB imports закомментированы в `bot/services/knowledge_search.py:21-22`:
```python
# FalkorDB imports закомментированы - требуют graphiti-core[falkordb]
# from bot.services.falkordb_service import get_falkordb_service
# from bot.services.simple_falkordb_service import get_simple_falkordb_service
```

**НЕ раскомментируй** без установки `pip install graphiti-core[falkordb]` в production!

---

## Константы и Environment

### Railway Production
```bash
# Project Configuration
PROJECT_ID="a470438c-3a6c-4952-80df-9e2c067233c6"
SERVICE_ID="3eb7a84e-5693-457b-8fe1-2f4253713a0c"
MYSQL_SERVICE_ID="d203ed15-2d73-405a-8210-4c100fbaf133"

# Production URLs
WEBHOOK_URL="https://ignatova-stroinost-bot-production.up.railway.app"
HEALTH_CHECK="https://ignatova-stroinost-bot-production.up.railway.app/health"
```

### Qdrant Cloud
```bash
QDRANT_URL="https://33d94c1b-cc7f-4b71-82cc-dcee289122f0.eu-central-1-0.aws.cloud.qdrant.io:6333"
QDRANT_COLLECTION="course_knowledge"
EMBEDDING_MODEL="all-MiniLM-L6-v2"  # sentence-transformers, 384D vectors
```

### Переключение систем поиска

**Использовать Qdrant** (рекомендуется для production):
```bash
USE_QDRANT=true
USE_SUPABASE=false
GRAPHITI_ENABLED=false
```

**Использовать Supabase** (для тестирования):
```bash
USE_SUPABASE=true
USE_QDRANT=false
GRAPHITI_ENABLED=false
```

См. подробности: `docs/QDRANT_SWITCH.md`

---

## Быстрые команды

### Development

```bash
# Локальный запуск
python main.py
# или с автоперезагрузкой
uvicorn main:app --reload --port 8000

# Установка зависимостей
pip install -r requirements.txt

# Создание виртуального окружения для миграции
python3 -m venv venv_fastembed
source venv_fastembed/bin/activate
pip install fastembed qdrant-client python-dotenv
```

### Мониторинг и диагностика

```bash
# Health check
curl https://ignatova-stroinost-bot-production.up.railway.app/health

# Статистика Qdrant
curl https://ignatova-stroinost-bot-production.up.railway.app/api/admin/qdrant/stats

# Статистика MySQL
curl https://ignatova-stroinost-bot-production.up.railway.app/api/stats

# Railway deployment мониторинг
python3 scripts/railway_monitor.py info          # Краткий статус
python3 scripts/railway_monitor.py monitor       # Непрерывный мониторинг
python3 scripts/railway_monitor.py logs          # Последние логи
```

### Webhook управление

```bash
# Установка webhook (в браузере или curl)
curl https://ignatova-stroinost-bot-production.up.railway.app/webhook/set

# Проверка статуса webhook
curl https://ignatova-stroinost-bot-production.up.railway.app/webhook/info
```

### Миграция базы знаний

```bash
# Qdrant миграция (локально)
python3 scripts/migrate_to_qdrant.py

# Supabase миграция
python3 scripts/migrate_to_supabase.py

# Парсинг базы знаний
python3 scripts/parse_knowledge_base.py
```

---

## Ключевые файлы и их назначение

### Конфигурация и инструкции
- `bot/config.py` - Все переменные окружения и feature flags
- `data/instruction.json` - Системная инструкция для AI (перезагружается через `/api/admin/reload-instruction`)

### AI Agent
- `bot/agent.py` - `TextilProAgent` класс:
  - `generate_response()` - Основная логика генерации (LLM routing, RAG pattern)
  - `search_knowledge_base()` - Поиск в векторной БД
  - `add_to_zep_memory()` / `get_zep_memory_context()` - Управление памятью
  - `call_llm()` - LLM router с fallback (OpenAI → Anthropic)

### Обработчики сообщений
- `bot/handlers/message_handler.py`:
  - `handle_regular_message()` - Текстовые сообщения
  - `handle_voice_message()` - Голосовые (Whisper API)
- `bot/handlers/business_handler.py`:
  - `_is_owner_message()` - Фильтрация владельца Business аккаунта
  - `handle_business_message()` - HTTP API отправка

### Векторный поиск
- `bot/services/knowledge_search.py`:
  - `KnowledgeSearchService` - Unified interface
  - `route_query()` - Query routing (semantic/fulltext/hybrid)
  - `_search_semantic()` - Multi-stage entity filtering
  - `format_context_for_llm()` - Форматирование результатов

---

## Debug и Troubleshooting

### Debug Endpoints

```bash
# DEBUG INFO в ответах бота (показывает статистику поиска)
DEBUG_INFO_ENABLED=true

# Проверка Zep Memory
GET /debug/zep-status

# Проверка Business connections
GET /debug/business-owners

# Детали сессии пользователя
GET /debug/memory/{session_id}

# Логи бота
GET /debug/logs
GET /debug/voice-logs
```

### Типичные проблемы

**1. AI agent не загружается (`ai_enabled: false`)**
- Проверь FalkorDB imports закомментированы (см. раздел 4 выше)
- Проверь логи: `python3 scripts/railway_monitor.py logs`

**2. Пустые результаты поиска**
- Проверь миграцию завершена: `curl .../api/admin/qdrant/stats`
- Проверь `USE_QDRANT=true` или `USE_SUPABASE=true` установлен
- Проверь `min_relevance` threshold не слишком высокий (default: 0.3)

**3. Webhook сбрасывается после деплоя**
- Используй прямой Telegram API вызов (не `bot.set_webhook()`)
- См. `main.py:258-301` - requests.post с allowed_updates

**4. Brainwrites в результатах поиска**
- Проверь multi-stage search включён в `knowledge_search.py`
- Проверь entity_type filters работают

### Graceful Degradation

Бот продолжает работать при сбое отдельных компонентов:
- MySQL недоступен → логи warnings
- Qdrant/Graphiti недоступен → fallback на локальные файлы
- Zep недоступен → fallback на локальную память
- OpenAI недоступен → fallback на Anthropic Claude

---

## Важные замечания

### При внесении изменений

1. **ВСЕГДА** коммить в Git (см. раздел "Git и Deployment Workflow")
2. **ВСЕГДА** проверять логи деплоя через 90 секунд
3. **ИСПОЛЬЗОВАТЬ** `railway_monitor.py` для мониторинга
4. **ОБНОВЛЯТЬ** соответствующую документацию в `docs/`

### При возникновении проблем

1. Проверь `docs/DEPLOYMENT_HISTORY.md` - история критических исправлений
2. Используй debug endpoints для диагностики
3. Проверь Railway логи: `python3 scripts/railway_monitor.py logs`
4. Используй `DEBUG_INFO_ENABLED=true` для детального анализа

### Производительность

**Metrics:**
- Startup time: <5 секунд
- Search latency: 30-50ms (Qdrant), 100-250ms (Supabase)
- Response time: 100-300ms (AI generation)

**Cost optimization:**
- GPT-4o-mini вместо GPT-4o (экономия 15-17x)
- Локальные embeddings (fastembed) вместо OpenAI API
- Обработка knowledge base: $2-3 за 1000 entities

---

## Документация

### Основные документы
- `README.md` - Обзор и quick start
- `CLAUDE.md` - Этот файл (guide for Claude Code)
- `SUCCESS_REPORT.md` - Полный отчёт о запуске бота
- `FIX_GUIDE.md` - Гайд по устранению проблем
- `RAILWAY_API.md` - Работа с Railway API

### Техническая документация (docs/)
- `QDRANT_INTEGRATION.md` - Qdrant vector database setup
- `SUPABASE_INTEGRATION.md` - Supabase vector store setup
- `GRAPHITI_INTEGRATION.md` - Knowledge graph (deprecated)
- `MEMORY_ARCHITECTURE.md` - Гибридная архитектура памяти
- `DEPLOYMENT_HISTORY.md` - История критических исправлений

**Последнее обновление:** 25 ноября 2025
**Версия:** 2.1 (Claude Code optimized)
