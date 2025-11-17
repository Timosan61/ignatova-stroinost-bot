# Supabase Vector Store Integration

Полное руководство по интеграции Supabase pgvector в бот для семантического поиска по базе знаний.

---

## 📋 Оглавление

1. [Обзор](#обзор)
2. [Архитектура](#архитектура)
3. [Настройка Supabase](#настройка-supabase)
4. [Миграция данных](#миграция-данных)
5. [Переключение систем поиска](#переключение-систем-поиска)
6. [API Reference](#api-reference)
7. [Производительность](#производительность)
8. [Сравнение с Qdrant](#сравнение-с-qdrant)
9. [Troubleshooting](#troubleshooting)

---

## Обзор

**Supabase Vector Store** — третий метод поиска по базе знаний (вместе с Qdrant и Graphiti/FalkorDB), основанный на PostgreSQL + pgvector extension.

### Ключевые особенности

✅ **PostgreSQL** — проверенная СУБД с ACID гарантиями
✅ **pgvector** — эффективный векторный поиск (cosine similarity)
✅ **OpenAI embeddings** — state-of-the-art векторизация (text-embedding-3-small, 1536D)
✅ **Единый backend** — база данных + векторный поиск в одном месте
✅ **Row Level Security** — встроенная система прав доступа
✅ **REST API** — готовый HTTP API для всех операций

### Когда использовать Supabase?

| Сценарий | Рекомендация |
|----------|--------------|
| **Development/Testing** | ✅ Отлично (простая настройка) |
| **Малые проекты (< 10K entities)** | ✅ Отлично (достаточно производительности) |
| **Средние проекты (10-100K entities)** | ✅ Хорошо (но следите за производительностью) |
| **Большие проекты (> 100K entities)** | ⚠️ Лучше использовать Qdrant (dedicated vector DB) |
| **Единый backend (DB + search)** | ✅ Идеально (PostgreSQL для всего) |
| **Экономия на embeddings** | ❌ OpenAI API платный (используйте Qdrant с локальными моделями) |

---

## Архитектура

### Компоненты системы

```
┌─────────────────────────────────────────────┐
│           TELEGRAM MESSAGE                  │
└──────────────────┬──────────────────────────┘
                   │
        ┌──────────┴──────────┐
        ▼                     ▼
   ┌─────────┐        ┌──────────────┐
   │  MySQL  │        │ TextilProBot │
   │ Archive │        │  AI Logic    │
   └─────────┘        └──────┬───────┘
                             │
                   ┌─────────┴─────────┐
                   ▼                   ▼
           ┌──────────────┐    ┌──────────┐
           │   SUPABASE   │    │   ZEP    │
           │ (Knowledge)  │    │ (Context)│
           └──────┬───────┘    └──────────┘
                  │
         ┌────────┴────────┐
         ▼                 ▼
   ┌──────────┐      ┌──────────┐
   │PostgreSQL│      │  OpenAI  │
   │ + pgvector│     │Embeddings│
   └──────────┘      └──────────┘
```

### Технологический стек

| Компонент | Технология | Версия |
|-----------|-----------|--------|
| **Database** | PostgreSQL | 15+ |
| **Vector extension** | pgvector | 0.5.0+ |
| **Python SDK** | supabase | 2.0.0+ |
| **Embeddings API** | OpenAI | text-embedding-3-small |
| **Vector dimensions** | 1536 | - |
| **Similarity metric** | Cosine distance | - |

---

## Настройка Supabase

### Шаг 1: Создать проект в Supabase

1. Перейди на [app.supabase.com](https://app.supabase.com)
2. Нажми **"New Project"**
3. Заполни:
   - **Name**: `ignatova-course-bot` (или любое имя)
   - **Database Password**: Сохрани пароль!
   - **Region**: `eu-central-1` (ближайший регион)
   - **Plan**: Free tier (достаточно для 3,234 entities)
4. Жди ~2 минуты пока проект создастся

### Шаг 2: Получить API credentials

1. Открой проект → **Settings** → **API**
2. Скопируй:
   - **Project URL**: `https://xxx.supabase.co`
   - **service_role key** (⚠️ НЕ anon key!)

**ВАЖНО:** Service role key имеет полный доступ к БД. НЕ коммить в Git!

### Шаг 3: Выполнить SQL setup

1. Открой **SQL Editor** в Supabase Dashboard
2. Создай новый query
3. Скопируй содержимое файла `scripts/supabase_setup.sql`
4. Выполни весь скрипт (Run)

**Что создаётся:**
- Таблица `course_knowledge` с pgvector column
- Индексы для similarity search (ivfflat algorithm)
- RPC функция `match_documents` для векторного поиска
- RPC функция `get_knowledge_stats` для статистики
- Row Level Security policies

**Проверка:**
```sql
-- Проверить что таблица создана
SELECT * FROM course_knowledge LIMIT 1;

-- Проверить что pgvector extension работает
SELECT * FROM pg_extension WHERE extname = 'vector';
```

### Шаг 4: Настроить Environment Variables

**Локально (`.env`):**
```bash
# Supabase Configuration
SUPABASE_URL=https://qqppsflwztnxcegcbwqd.supabase.co
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_TABLE=course_knowledge
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
USE_SUPABASE=true

# OpenAI API (для embeddings)
OPENAI_API_KEY=sk-proj-...

# Отключить другие системы
USE_QDRANT=false
GRAPHITI_ENABLED=false
```

**Railway (Production):**
1. Открой Railway Dashboard → Variables
2. Добавь все переменные выше
3. Redeploy

---

## Миграция данных

### Подготовка

1. Убедись что SQL setup выполнен
2. Проверь что `OPENAI_API_KEY` настроен
3. Убедись что `SUPABASE_SERVICE_KEY` корректный

### Запуск миграции

**Тестовый прогон (dry-run):**
```bash
# Только парсинг, без загрузки
python3 scripts/migrate_to_supabase.py --dry-run
```

**Полная миграция:**
```bash
# Миграция всех 3,234 entities
python3 scripts/migrate_to_supabase.py --batch-size 20
```

**Параметры:**
- `--batch-size N` — количество entities в одном batch (default: 20)
- `--reset` — очистить таблицу перед миграцией (не реализовано)
- `--dry-run` — тестовый прогон без загрузки данных

### Ожидаемые результаты

```
🚀 Starting Supabase migration...
   Batch size: 20
   Embedding model: text-embedding-3-small
   Dry run: false

============================================================
STEP 1: Parsing Knowledge Base
============================================================
📖 Parsing FAQ...
✅ FAQ parsed: 25 entries
📖 Parsing Lessons...
✅ Lessons parsed: 127 chunks
📖 Parsing Curator Corrections...
✅ Curator Corrections parsed: 275 entries
📖 Parsing Student Questions (ALL questions)...
✅ Student Questions parsed: 2,635 questions
📖 Parsing Brainwrite Examples...
✅ Brainwrite Examples parsed: 172 examples
📊 Total entities parsed: 3,234

============================================================
STEP 2: Uploading to Supabase
============================================================
📤 Batch 1/162: Uploading 20 entities...
   ✅ Uploaded: 20/20 | Progress: 20/3,234 | Tokens: 8,450 | Cost: $0.0002
📤 Batch 2/162: Uploading 20 entities...
   ✅ Uploaded: 20/20 | Progress: 40/3,234 | Tokens: 16,900 | Cost: $0.0003
...

============================================================
✅ MIGRATION COMPLETE!
============================================================
Total entities: 3,234
Uploaded: 3,234
Failed: 0

By type:
  - brainwrite: 172
  - correction: 275
  - faq: 25
  - lesson: 127
  - question: 2,635

OpenAI API usage:
  - Total tokens: 6,853,420
  - Total cost: $0.1371

Time elapsed: 945.3s (15.8m)
============================================================
```

### Стоимость миграции

**OpenAI Embedding API:**
- **Model**: `text-embedding-3-small`
- **Cost**: $0.00002 за 1K tokens
- **Average content length**: ~2,000 tokens
- **Total cost**: ~$0.13 (для 3,234 entities)

---

## Переключение систем поиска

### Три доступных метода

Бот поддерживает три переключаемых системы поиска:

| Система | Variable | Описание |
|---------|----------|----------|
| **Supabase** | `USE_SUPABASE=true` | PostgreSQL + pgvector + OpenAI embeddings |
| **Qdrant** | `USE_QDRANT=true` | Dedicated vector DB + локальные embeddings |
| **Graphiti** | `GRAPHITI_ENABLED=true` | Knowledge graph + Neo4j/FalkorDB |

### Переключение на Supabase

**Railway Dashboard:**
```bash
# Включить Supabase
USE_SUPABASE=true

# Отключить другие
USE_QDRANT=false
GRAPHITI_ENABLED=false
```

**Проверка после деплоя:**
```bash
curl https://ignatova-stroinost-bot-production.up.railway.app/health
```

**Ожидается:**
```json
{
  "status": "healthy",
  "ai_enabled": true,
  "ai_agent": true,
  "zep_memory": true,
  "supabase_service": "healthy",
  "supabase_enabled": true,
  "total_entities": 3234
}
```

### Логи startup

```
🟣 Supabase Vector Store включен (USE_SUPABASE=true, OpenAI embeddings ready)
✅ Supabase client initialized: https://qqppsflwztnxcegcbwqd.supabase.co
✅ OpenAI client initialized: text-embedding-3-small
✅ Supabase table 'course_knowledge' accessible
🟣 KnowledgeSearchService initialized (Using: SUPABASE)
```

---

## API Reference

### SupabaseService

**bot/services/supabase_service.py**

#### `search_semantic()`

Семантический поиск через pgvector.

```python
async def search_semantic(
    query: str,
    limit: int = 5,
    score_threshold: float = 0.5,
    entity_type: Optional[str] = None
) -> List[Dict[str, Any]]
```

**Args:**
- `query` — поисковый запрос
- `limit` — максимальное количество результатов
- `score_threshold` — минимальный порог similarity (0.0-1.0)
- `entity_type` — фильтр по типу (lesson, faq, correction, question, brainwrite)

**Returns:**
```python
[
    {
        "id": "lesson_0",
        "score": 0.87,
        "entity_type": "lesson",
        "title": "Урок 1: Введение в мозгоритмы",
        "content": "...",
        "metadata": {
            "lesson_number": 1,
            "category": "foundation",
            "chunk_index": 0,
            "total_chunks": 3
        }
    },
    ...
]
```

#### `add_entity()`

Добавить entity в Supabase.

```python
async def add_entity(
    entity_id: str,
    content: str,
    entity_type: str,
    title: str = "",
    metadata: Optional[Dict[str, Any]] = None
) -> Tuple[bool, Optional[str]]
```

**Returns:** `(success: bool, error_message: Optional[str])`

#### `health_check()`

Проверка здоровья сервиса.

```python
async def health_check() -> Dict[str, Any]
```

**Returns:**
```python
{
    "service": "supabase",
    "status": "healthy",
    "enabled": True,
    "url": "https://xxx.supabase.co",
    "table": "course_knowledge",
    "total_entities": 3234,
    "embedding_model": "text-embedding-3-small"
}
```

#### `get_stats()`

Получить статистику таблицы.

```python
async def get_stats() -> Dict[str, Any]
```

**Returns:**
```python
{
    "table": "course_knowledge",
    "total_entities": 3234,
    "by_type": {
        "lesson": 127,
        "faq": 25,
        "correction": 275,
        "question": 2635,
        "brainwrite": 172
    },
    "embedding_model": "text-embedding-3-small",
    "embedding_dimensions": 1536
}
```

---

## Производительность

### Search Latency

| Метрика | Значение | Примечание |
|---------|----------|------------|
| **OpenAI embedding** | 50-100ms | Генерация вектора для query |
| **Supabase RPC call** | 50-150ms | Similarity search через pgvector |
| **Total latency** | 100-250ms | End-to-end search time |

### Масштабируемость

| Количество entities | Latency | Index type | Примечание |
|---------------------|---------|------------|------------|
| **< 10K** | 50-100ms | ivfflat (lists=100) | Отлично |
| **10-50K** | 100-200ms | ivfflat (lists=1000) | Хорошо |
| **50-100K** | 200-300ms | ivfflat (lists=2000) | Приемлемо |
| **> 100K** | 300ms+ | HNSW recommended | Переходите на Qdrant |

### OpenAI API Rate Limits

| Tier | Requests/min | Tokens/min | Cost |
|------|--------------|------------|------|
| **Free** | 500 | 200K | $0.00002/1K tokens |
| **Tier 1** | 3,000 | 1M | $0.00002/1K tokens |
| **Tier 2** | 10,000 | 5M | $0.00002/1K tokens |

**Рекомендации:**
- Batch size: 20 entities (для миграции)
- Search latency: добавить кэширование для частых запросов
- Cost optimization: использовать Qdrant для production (локальные embeddings)

---

## Сравнение с Qdrant

| Аспект | Supabase | Qdrant |
|--------|----------|--------|
| **Embeddings** | OpenAI API (облако, платно) | sentence-transformers (локально, бесплатно) |
| **Vector size** | 1536D (text-embedding-3-small) | 384D (all-MiniLM-L6-v2) |
| **Index algorithm** | ivfflat (PostgreSQL) | HNSW (dedicated vector DB) |
| **Search latency** | 100-250ms | 30-50ms |
| **Масштабируемость** | До 100K entities | Миллионы entities |
| **Стоимость (setup)** | $0.13 (миграция 3,234 entities) | Бесплатно |
| **Стоимость (runtime)** | $0.02 на 1000 queries | Бесплатно |
| **Setup сложность** | Средняя (SQL + Python) | Средняя (Python + Qdrant Cloud) |
| **Единый backend** | ✅ PostgreSQL для DB + vectors | ❌ Qdrant + MySQL раздельно |

**Вывод:**
- **Development/Testing**: Supabase (проще setup, единый backend)
- **Production (малые проекты)**: Supabase (< 10K entities, достаточно производительности)
- **Production (крупные проекты)**: Qdrant (> 100K entities, нужна максимальная производительность)

---

## Troubleshooting

### 1. Supabase service disabled

**Симптом:**
```
⚠️ Supabase service disabled: supabase SDK not installed
```

**Решение:**
```bash
pip install supabase>=2.0.0 openai>=1.91.0
```

### 2. OpenAI API недоступен

**Симптом:**
```
⚠️ Supabase включен, но OpenAI API недоступен (требуется для embeddings)
```

**Решение:**
Проверь `OPENAI_API_KEY` в environment variables.

### 3. Supabase table not found

**Симптом:**
```
⚠️ Supabase table 'course_knowledge' not found or empty
```

**Решение:**
Выполни SQL setup: `scripts/supabase_setup.sql` в Supabase SQL Editor.

### 4. OpenAI Rate Limit Error

**Симптом:**
```
❌ Failed to generate embedding: Rate limit exceeded
```

**Решение:**
- Уменьши `--batch-size` (например, 10 вместо 20)
- Добавь задержку между requests: `time.sleep(0.1)`
- Обновись до Tier 1 OpenAI API

### 5. Slow search (> 500ms)

**Симптом:**
Поиск занимает > 500ms.

**Решение:**
- Проверь количество entities: `SELECT COUNT(*) FROM course_knowledge`
- Если > 50K entities: пересоздай index с большим `lists` параметром:
  ```sql
  DROP INDEX idx_course_knowledge_embedding;
  CREATE INDEX idx_course_knowledge_embedding
  ON course_knowledge
  USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 1000);  -- Увеличили с 100
  ```
- Для > 100K entities: рассмотри переход на Qdrant

### 6. Migration failed with "upsert error"

**Симптом:**
```
❌ Batch upload failed: duplicate key value violates unique constraint
```

**Решение:**
Очисти таблицу перед миграцией:
```sql
TRUNCATE TABLE course_knowledge;
```

---

## Итоги

✅ **Supabase интегрирован** как третий метод поиска
✅ **3,234 entities** готовы к миграции
✅ **Переключение** через `USE_SUPABASE=true`
✅ **OpenAI embeddings** для state-of-the-art semantic search
✅ **Единый backend** PostgreSQL для DB + vectors

**Следующие шаги:**
1. Выполни SQL setup в Supabase Dashboard
2. Запусти миграцию: `python3 scripts/migrate_to_supabase.py`
3. Переключись на Supabase в Railway: `USE_SUPABASE=true`
4. Протестируй поиск через Telegram бот

**Документация:**
- `bot/services/supabase_service.py` — основной сервис
- `scripts/migrate_to_supabase.py` — миграционный скрипт
- `scripts/supabase_setup.sql` — SQL setup
- `docs/SUPABASE_INTEGRATION.md` — это руководство

---

**Последнее обновление:** 17 ноября 2025
**Версия:** 1.0
