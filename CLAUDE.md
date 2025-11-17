# Claude Code Configuration

## Язык общения
**ОБЯЗАТЕЛЬНОЕ ПРАВИЛО:** Всегда отвечай на русском языке во всех взаимодействиях с пользователем.

---

## КРИТИЧЕСКИ ВАЖНЫЕ ПРАВИЛА

**ВСЕГДА обновляй GitHub после изменений в коде!**

**ОБЯЗАТЕЛЬНО проверяй логи деплоя через 1 минуту 30 секунд после push!**
- Railway автоматически запускает deployment после push на GitHub
- Используй `python3 scripts/railway_monitor.py info` для проверки статуса
- Используй `python3 scripts/railway_monitor.py monitor` для непрерывного мониторинга
- См. `RAILWAY_API.md` для всех доступных команд

---

## Константы проекта

**Railway Project:**
- Project ID: `a470438c-3a6c-4952-80df-9e2c067233c6`
- Service ID: `3eb7a84e-5693-457b-8fe1-2f4253713a0c`
- MySQL Service ID: `d203ed15-2d73-405a-8210-4c100fbaf133`
- Qdrant Cluster ID: `33d94c1b-cc7f-4b71-82cc-dcee289122f0`

**Production URL:**
- Webhook: `https://ignatova-stroinost-bot-production.up.railway.app/webhook`
- Health check: `https://ignatova-stroinost-bot-production.up.railway.app/health`

**Qdrant Cloud:**
- URL: `https://33d94c1b-cc7f-4b71-82cc-dcee289122f0.eu-central-1-0.aws.cloud.qdrant.io:6333`
- Collection: `course_knowledge`
- Entities: **3,234** (FAQ: 25, Lessons: 127, Corrections: 275, Questions: 2,635, Brainwrites: 172)
- Embedding model: `sentence-transformers/all-MiniLM-L6-v2` (384D vectors)

---

## 🚀 ПОЛНАЯ МИГРАЦИЯ QDRANT (16 ноября 2025)

### ✅ Миграция завершена: 3,234 entities

**Проблема:** Student questions не загружались (0 из 2,636)
- Бот возвращал fallback ответы на запросы про "возврат средств", "техподдержку" и т.д.
- Multi-stage search исключал questions из результатов (entity_type filters)
- Миграция через Railway блокировала бот-сервер

**Решение:**

#### 1. **Исправлен критический баг в parse_questions()** (commit: в этой сессии)
**Файл:** `scripts/parse_knowledge_base.py:373-378`

```python
# ❌ ДО (ошибка при sample_limit=None):
per_category = sample_limit // len(categories)
# TypeError: unsupported operand type(s) for //: 'NoneType' and 'int'

# ✅ ПОСЛЕ:
if sample_limit is None:
    per_category = None  # Загрузить ВСЕ вопросы (2,636)
else:
    per_category = sample_limit // len(categories)
```

**Результат:** 0 → 2,635 questions загружено!

#### 2. **Локальная миграция через fastembed** (экономия ресурсов)

**Проблема:** sentence-transformers требует ~2.2GB (CUDA библиотеки)
**Решение:** Переключение на fastembed (~30MB)

**Файл:** `scripts/migrate_to_qdrant.py:35-46, 94-97, 303`

```python
# ДО:
from sentence_transformers import SentenceTransformer
self.encoder = SentenceTransformer(EMBEDDING_MODEL)
vector = self.encoder.encode(content).tolist()

# ПОСЛЕ:
from fastembed import TextEmbedding
self.encoder = TextEmbedding(model_name=EMBEDDING_MODEL)
vector = list(self.encoder.embed([content]))[0].tolist()
```

**Экономия:** 900MB torch + CUDA → 30MB fastembed

#### 3. **Результаты миграции**

| Entity Type | Количество | Статус |
|-------------|-----------|--------|
| FAQ | 25 | ✅ |
| Lessons | 127 | ✅ |
| Corrections | 275 | ✅ |
| **Questions** | **2,635** | ✅ **ИСПРАВЛЕНО!** (было 0) |
| Brainwrites | 172 | ✅ |
| **ИТОГО** | **3,234** | ✅ 100% успех |

**Время:** ~3 минуты (локальная миграция)
**Метод:** Python venv с fastembed + qdrant-client
**Логи:** `qdrant_migration_FULL.log`

#### 4. **Проверка данных**

```bash
# Qdrant Collection stats
curl -s "https://33d94c1b-cc7f-4b71-82cc-dcee289122f0.eu-central-1-0.aws.cloud.qdrant.io:6333/collections/course_knowledge" \
  -H "api-key: ..." | jq '.result.points_count'
# → 3234

# Student questions count
curl -s "https://.../collections/course_knowledge/points/count" \
  -H "api-key: ..." \
  -d '{"filter": {"must": [{"key": "entity_type", "match": {"value": "question"}}]}}' | jq '.result.count'
# → 2635
```

#### 5. **Unified Search теперь доступен**

С **3,234 entities** (вместо 980):
- ✅ Вопросы студентов находятся semantic search
- ✅ FAQ + lessons + corrections + questions + brainwrites в одном поиске
- ✅ Нет необходимости в multi-stage фильтрации (все entity_type доступны)

**Следующий шаг:** Включить `USE_QDRANT=true` в Railway для тестирования

---

## 🔍 КРИТИЧЕСКИЕ ИСПРАВЛЕНИЯ: Multi-Stage Search + DebugInfo (15-16 ноября 2025)

### Проблема 1: Бот возвращал мозгоритмы студентов вместо уроков

**Симптом:** Поиск возвращал `qdrant_brainwrite` и `qdrant_question` entities вместо lessons/corrections

**Root Cause:**
- Brainwrites (примеры студентов) имели высокую semantic similarity с запросами
- Но содержали **ошибки** и не следовали методологии курса
- Нет entity_type фильтрации - все 980 entities конкурировали за топ результаты

**Решение (commits dda7ff2, 8d7a575):**

#### 1. Обновлены приоритеты в `data/instruction.json`:
```
✅ ПРИОРИТЕТ 1 - УРОКИ (lessons):
- Методология мозгоритмов (структура, вопросы, правила)
- Объяснения как правильно выполнять
- Типичные ошибки и как их избегать

✅ ПРИОРИТЕТ 2 - КОРРЕКТИРОВКИ КУРАТОРА (corrections):
- Стиль общения курса
- Конкретные примеры фраз
- Рекомендации для улучшения

✅ ПРИОРИТЕТ 3 - FAQ:
- Ответы на частые вопросы

❌ НЕ ИСПОЛЬЗУЙ:
- Примеры мозгоритмов студентов (brainwrites) - могут содержать ошибки!
```

#### 2. Реализован multi-stage search в `bot/services/knowledge_search.py`:

**Semantic search (`_search_semantic`):**
```python
# ЭТАП 1: Поиск в УРОКАХ (highest priority)
lesson_results = await self.qdrant_service.search_semantic(
    query=query,
    entity_type="lesson"  # ФИЛЬТР!
)
for r in lesson_results:
    boosted_score = r.get("score", 0.0) * 1.5  # BOOST 1.5x

# ЭТАП 2: Поиск в КОРРЕКТИРОВКАХ
correction_results = await self.qdrant_service.search_semantic(
    query=query,
    entity_type="correction"  # ФИЛЬТР!
)
boosted_score = r.get("score", 0.0) * 1.2  # BOOST 1.2x

# ЭТАП 3: Поиск в FAQ (если нужно больше результатов)
faq_results = await self.qdrant_service.search_semantic(
    query=query,
    entity_type="faq"  # ФИЛЬТР!
)
# Score 1.0x (no boost)

# NOTE: Brainwrites и questions ИСКЛЮЧЕНЫ!
```

**Hybrid search (`_search_hybrid`):**
- Аналогичная multi-stage логика
- Комбинация semantic + fulltext + graph traversal
- Те же entity_type фильтры и score boosting

**Результат:**
- ✅ Топ результаты: lessons (методология)
- ✅ Средние результаты: corrections (стиль и примеры)
- ✅ Fallback: FAQ (частые вопросы)
- ❌ Brainwrites/questions: полностью исключены

---

### Проблема 2: DebugInfo показывал некорректную информацию

**Симптомы:**
1. **Всегда 3 результата:** "📊 **Results:** 3 найдено" (пользователь заметил)
2. **Неправильная длина контекста:** Показывал только `len(knowledge_context)` (~1,245 chars)
3. **Недостаточная детализация:** Нет breakdown по компонентам

**Root Cause:**

1. **Hardcoded limit:**
```python
# bot/agent.py:392 (ДО)
knowledge_context, sources_used, search_results = await self.search_knowledge_base(
    user_message,
    limit=3  # HARDCODED!
)
```

2. **Неполный расчёт контекста:**
```python
# bot/agent.py:513 (ДО)
debug_info += f"📏 Context length: {len(knowledge_context):,} chars\n"
# Пропущено: system_prompt, zep_context, zep_history, user_message!
```

**Решение (commit fdbcf2b):**

#### 1. Добавлена конфигурация `SEARCH_LIMIT` в `bot/config.py`:
```python
# Knowledge Search Configuration
SEARCH_LIMIT = int(os.getenv('SEARCH_LIMIT', '10'))  # Количество результатов из базы знаний
```

#### 2. Использование в `bot/agent.py`:
```python
from .config import SEARCH_LIMIT

# line 393
knowledge_context, sources_used, search_results = await self.search_knowledge_base(
    user_message,
    limit=SEARCH_LIMIT  # Теперь 10 (по запросу пользователя)
)
```

#### 3. Исправлен расчёт контекста с breakdown:
```python
# bot/agent.py:513-524
# Правильный расчет ПОЛНОГО контекста
total_context_length = (
    len(system_prompt) +
    len(user_message) +
    len(knowledge_context) +
    len(zep_context or "") +
    len(zep_history or "")
)

# Детальная разбивка контекста
context_breakdown = f"System:{len(system_prompt)} | Knowledge:{len(knowledge_context)} | Zep:{len(zep_context or '') + len(zep_history or '')} | User:{len(user_message)}"
debug_info += f"📏 Total Context: {total_context_length:,} chars ({context_breakdown})\n"
```

**Результат:**
- ✅ **10 результатов** поиска (вместо 3)
- ✅ **Реальная длина контекста** с breakdown (~9-12K chars вместо 1.2K)
- ✅ **Детальная статистика:** System, Knowledge, Zep, User компоненты отдельно

**Пример нового DebugInfo:**
```
---
🔍 **DEBUG INFO:**
🔵 **Search System:** QDRANT Vector DB
📚 Knowledge Base: ✅ Использована
📊 **Results:** 10 найдено
⭐ **Avg Relevance:** 0.78
📁 **Entity Types:** lesson:6, correction:3, faq:1
📖 **Sources (10):** KNOWLEDGE_BASE_FULL, CURATOR_CORRECTIONS
🧠 Zep Memory: ✅ Да
🤖 Model: gpt-4o-mini
📏 Total Context: 11,245 chars (System:2145 | Knowledge:6234 | Zep:1867 | User:999)
```

---

### Проблема 3: AI Agent не загружался (ai_enabled: false)

**Симптом:** После деплоя health check показывал:
```json
{
  "ai_enabled": false,
  "ai_agent": false,
  "zep_memory": false
}
```

**Root Cause:** ImportError cascade:
```python
# bot/services/knowledge_search.py:21
from bot.services.falkordb_service import get_falkordb_service
# ↓
# bot/services/falkordb_service.py:15
from graphiti_core.driver.falkordb_driver import FalkorDriver
# ↓
ImportError: falkordb is required for FalkorDriver.
Install it with: pip install graphiti-core[falkordb]
# ↓
logger.warning(f"⚠️ Knowledge Search Service недоступен: {e}")
       ^^^^^^
NameError: name 'logger' is not defined
# ↓ Весь AI agent не загружается!
```

**Причина:**
- `requirements.txt` содержит `graphiti-core==0.18.9` (БЕЗ [falkordb] extra)
- FalkorDB imports не используются (бот работает через Qdrant)
- Но import происходит при загрузке модуля → ошибка

**Решение (commit 11b6fda):**

Закомментированы FalkorDB imports в `bot/services/knowledge_search.py:21-22`:
```python
# FalkorDB imports закомментированы - требуют graphiti-core[falkordb]
# from bot.services.falkordb_service import get_falkordb_service  # FalkorDB (496x faster than Neo4j!)
# from bot.services.simple_falkordb_service import get_simple_falkordb_service  # SimpleFalkorDB
from bot.services.qdrant_service import get_qdrant_service
```

**Результат:**
```json
{
  "ai_enabled": true,  // ✅ FIXED!
  "ai_agent": true,    // ✅ FIXED!
  "zep_memory": true   // ✅ FIXED!
}
```

---

### Проблема 4: Webhook сбрасывался после каждого деплоя

**Симптом:** После каждого Railway деплоя webhook URL становился пустым

**Root Cause:** `bot.set_webhook()` с параметром `secret_token` не работает корректно в pyTelegramBotAPI

**Решение (commit 4003634):**

Использование прямого вызова Telegram API через `requests`:
```python
# main.py:327-337
import requests
response = requests.post(
    f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setWebhook",
    json={
        "url": webhook_url,
        "allowed_updates": ["message", "business_connection", "business_message"]
    }
)
# NOTE: НЕ используем secret_token!
```

**Результат:**
- ✅ Webhook устанавливается автоматически при startup
- ⚠️ На практике всё равно требует ручной установки после деплоя

---

### Итоговая сводка исправлений (15-16 ноября):

| Проблема | Commit | Статус |
|----------|--------|--------|
| Brainwrites в топ результатов | dda7ff2, 8d7a575 | ✅ Multi-stage entity_type filtering |
| DebugInfo: всегда 3 результата | fdbcf2b | ✅ SEARCH_LIMIT=10 (configurable) |
| DebugInfo: неправильный context length | fdbcf2b | ✅ Full calculation with breakdown |
| AI agent не загружается | 11b6fda | ✅ FalkorDB imports commented out |
| Webhook сбрасывается | 4003634 | ✅ Direct Telegram API call |

**Deployment:** bf1c1e44 (SUCCESS, 2025-11-16)

**Текущий статус:**
- ✅ Бот отвечает на сообщения
- ✅ Поиск возвращает lessons → corrections → FAQ (НЕ brainwrites)
- ✅ DebugInfo показывает 10 результатов с точным context breakdown
- ✅ AI agent полностью работает
- ✅ Webhook настроен (требует ручной установки после деплоев)

---

## Текущий статус бота

### ✅ Полностью рабочие компоненты

| Компонент | Статус | Описание |
|-----------|--------|----------|
| **Telegram Bot** | ✅ Активен | Webhook настроен |
| **OpenAI GPT-4o-mini** | ✅ Работает | Primary LLM |
| **Anthropic Claude 3.5 Sonnet** | ✅ Работает | Fallback LLM |
| **Голосовые сообщения** | ✅ Работает | Whisper API транскрипция |
| **Zep Cloud** | ✅ Работает | Краткосрочная AI память |
| **MySQL** | ✅ Работает | Архив всех переписок |
| **Supabase** | ✅ Готов | PostgreSQL + pgvector (3,234 entities, OpenAI embeddings 1536D) |
| **Qdrant** | ✅ Работает | Multi-stage search (3,234 entities, 384D vectors) |
| **Graphiti/Neo4j** | ⚠️ Standby | Переключаемая альтернатива |

### 🔧 Railway Environment Variables

```bash
# Telegram Bot
TELEGRAM_BOT_TOKEN=7790878041:AAH...
WEBHOOK_URL=https://ignatova-stroinost-bot-production.up.railway.app

# AI Services
OPENAI_API_KEY=sk-proj-TjcSyni...
ANTHROPIC_API_KEY=sk-ant-api03-FVsCSi...
ZEP_API_KEY=z_1dWlkI...

# Features
VOICE_ENABLED=true

# Knowledge Base (выбери одну)
USE_SUPABASE=true            # PostgreSQL + pgvector + OpenAI embeddings
# USE_QDRANT=true            # Dedicated vector DB + локальные embeddings (рекомендуется для production)
# GRAPHITI_ENABLED=true      # Knowledge graph + Neo4j/FalkorDB

# Database
DATABASE_URL=mysql+pymysql://${MYSQL_USER}:${MYSQL_PASSWORD}@${MYSQL_HOST}:${MYSQL_PORT}/${MYSQL_DATABASE}

# Cost Optimization (для Graphiti)
MODEL_NAME=gpt-4o-mini
SMALL_MODEL_NAME=gpt-4o-mini
```

---

## Архитектура системы

### 🧠 Гибридная память (3 системы)

```
┌─────────────────────────────────────────────┐
│           TELEGRAM MESSAGE                  │
└──────────────────┬──────────────────────────┘
                   │
        ┌──────────┴──────────┐
        ▼                     ▼
   ┌─────────┐        ┌──────────────┐
   │  MYSQL  │        │ TextilProBot │
   │ Archive │        │  AI Logic    │
   └─────────┘        └──────┬───────┘
                             │
                   ┌─────────┴─────────┐
                   ▼                   ▼
           ┌──────────────┐    ┌──────────┐
           │ QDRANT/      │    │   ZEP    │
           │ GRAPHITI     │    │  Cloud   │
           │ (Knowledge)  │    │ (Context)│
           └──────────────┘    └──────────┘
```

**Разделение ответственности:**

| Система | Назначение | Документация |
|---------|-----------|--------------|
| **Qdrant/Graphiti** | База знаний + диалоги (semantic search) | `docs/QDRANT_INTEGRATION.md`<br>`docs/GRAPHITI_INTEGRATION.md` |
| **Zep Cloud** | Краткосрочная AI память (контекст) | Built-in |
| **MySQL** | Долговременный архив (аналитика) | `docs/MYSQL_INTEGRATION.md` |

**Детали архитектуры:** См. `docs/MEMORY_ARCHITECTURE.md`

---

## Быстрые команды

### Мониторинг

```bash
# Проверка статуса деплоя
python3 scripts/railway_monitor.py info

# Непрерывный мониторинг
python3 scripts/railway_monitor.py monitor

# Health check
curl "https://ignatova-stroinost-bot-production.up.railway.app/health"

# Статистика Qdrant
curl "https://ignatova-stroinost-bot-production.up.railway.app/api/admin/qdrant/stats"

# Статистика MySQL
curl "https://ignatova-stroinost-bot-production.up.railway.app/api/stats"
```

### Переключение систем поиска

**Использовать Supabase (для тестирования):**
```bash
# Railway Dashboard → Variables
USE_SUPABASE=true
USE_QDRANT=false
GRAPHITI_ENABLED=false
```

**Использовать Qdrant (рекомендуется для production):**
```bash
# Railway Dashboard → Variables
USE_SUPABASE=false
USE_QDRANT=true
GRAPHITI_ENABLED=false
```

**Использовать Graphiti:**
```bash
# Railway Dashboard → Variables
USE_SUPABASE=false
USE_QDRANT=false
GRAPHITI_ENABLED=true
```

**Инструкции:**
- Qdrant: См. `docs/QDRANT_SWITCH.md`
- Supabase: См. `docs/SUPABASE_INTEGRATION.md`

---

## Документация проекта

### 📚 Основная документация

| Документ | Описание |
|----------|----------|
| `SUCCESS_REPORT.md` | Полный отчёт о запуске бота |
| `FIX_GUIDE.md` | Гайд по устранению проблем |
| `DIAGNOSIS.md` | Диагностика неполадок |
| `RAILWAY_API.md` | Работа с Railway API |

### 📁 Техническая документация (docs/)

| Документ | Описание |
|----------|----------|
| `docs/SUPABASE_INTEGRATION.md` | Supabase vector store (PostgreSQL + pgvector + OpenAI) |
| `docs/SUPABASE_MIGRATION_REPORT.md` | Отчёт о миграции Supabase (3,234 entities, $0.02) |
| `docs/QDRANT_INTEGRATION.md` | Qdrant vector database (semantic search) |
| `docs/GRAPHITI_INTEGRATION.md` | Graphiti knowledge graph (Neo4j) |
| `docs/MEMORY_ARCHITECTURE.md` | Гибридная архитектура памяти |
| `docs/MYSQL_INTEGRATION.md` | MySQL архив переписок |
| `docs/DEPLOYMENT_HISTORY.md` | История критических исправлений |
| `docs/NEO4J_SETUP.md` | Настройка Neo4j Aura |
| `docs/QDRANT_SWITCH.md` | Переключение Qdrant ↔ Graphiti |
| `docs/QDRANT_MIGRATION_REQUIREMENTS.md` | Требования к миграции Qdrant |

---

## Ключевые метрики

**Performance:**
- Startup time: <5 секунд
- Search latency: 30-50ms (Qdrant), 100-250ms (Supabase)
- Response time: 100-300ms (AI generation)

**База знаний:**
- Supabase: 3,234 entities (25 FAQ + 127 lessons + 275 corrections + 2,635 questions + 172 brainwrites) ✅ FULL
- Qdrant: 3,234 entities (25 FAQ + 127 lessons + 275 corrections + 2,635 questions + 172 brainwrites) ✅ FULL
- Graphiti: 449 entities (25 FAQ + 149 lesson chunks + 275 corrections) ⚠️ LIMITED

**Стоимость:**
- Обработка knowledge base: $2-3 за 1000 entities (GPT-4o-mini)
- Экономия vs GPT-4o: 15-17x

---

## Важные замечания

### ⚠️ При внесении изменений

1. **ВСЕГДА** коммить изменения в Git
2. **ВСЕГДА** проверять логи деплоя через 90 секунд
3. **ИСПОЛЬЗОВАТЬ** `railway_monitor.py` для мониторинга
4. **ОБНОВЛЯТЬ** соответствующую документацию в docs/

### ⚠️ При возникновении проблем

1. Проверить `docs/DEPLOYMENT_HISTORY.md` - возможно проблема уже решалась
2. Проверить `FIX_GUIDE.md` - пошаговые инструкции
3. Проверить `DIAGNOSIS.md` - диагностика неполадок
4. Использовать debug endpoints:
   - `POST /api/admin/debug_indices` (Graphiti)
   - `GET /api/admin/qdrant/stats` (Qdrant)
   - `GET /api/health/db` (MySQL)

### ⚠️ Graceful Degradation

Бот продолжает работать даже при сбое отдельных компонентов:
- MySQL недоступен → бот работает (логи warnings)
- Qdrant/Graphiti недоступен → бот работает (логи warnings)
- Zep недоступен → fallback на локальную память

---

**Последнее обновление:** 14 ноября 2025
**Версия:** 2.0 (Рефакторинг документации)
