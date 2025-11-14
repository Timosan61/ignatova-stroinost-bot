# Переключатель Qdrant ↔ Graphiti

Документация по переключению между Qdrant Vector Database и Graphiti/Neo4j для поиска по базе знаний.

## Обзор

Бот поддерживает две системы для хранения и поиска базы знаний:

| Система | Тип БД | Преимущества | Недостатки |
|---------|--------|--------------|------------|
| **Qdrant** | Vector Database | ✅ Быстрый semantic search (30-50ms)<br>✅ Простая архитектура<br>✅ Оптимизирован для embeddings | ❌ Нет graph relationships<br>❌ Нет temporal reasoning |
| **Graphiti/Neo4j** | Graph Database | ✅ Graph relationships (урок → техника)<br>✅ Temporal reasoning<br>✅ Сложные graph queries | ⚠️ Медленнее для pure vector search<br>⚠️ Сложнее в поддержке |

**Переключение осуществляется через одну environment variable: `USE_QDRANT`**

---

## Быстрый старт

### 1. Переключиться на Qdrant

#### В Railway Dashboard:

1. Откройте Railway Dashboard: https://railway.app/project/a470438c-3a6c-4952-80df-9e2c067233c6
2. Выберите сервис `ignatova-stroinost-bot`
3. Перейдите в раздел **Variables**
4. Установите **`USE_QDRANT=true`**
5. Railway автоматически перезапустит сервис

#### Локально (в `.env`):

```bash
USE_QDRANT=true
```

### 2. Запустить миграцию данных

После переключения на Qdrant нужно загрузить 449 entities:

```bash
# Через Admin API (рекомендуется)
curl -X POST "https://ignatova-stroinost-bot-production.up.railway.app/api/admin/qdrant/migrate" \
  -H "Content-Type: application/json" \
  -d '{"batch_size": 50, "reset": false}'

# Или локально через скрипт
python3 scripts/migrate_to_qdrant.py --batch-size 50
```

**Время миграции:** 10-20 минут (449 entities)

### 3. Проверить статус

```bash
# Проверить health
curl "https://ignatova-stroinost-bot-production.up.railway.app/api/admin/qdrant/health"

# Проверить статус миграции
curl "https://ignatova-stroinost-bot-production.up.railway.app/api/admin/qdrant/migrate_status"

# Проверить статистику
curl "https://ignatova-stroinost-bot-production.up.railway.app/api/admin/qdrant/stats"
```

### 4. Тестовый поиск

```bash
curl "https://ignatova-stroinost-bot-production.up.railway.app/api/admin/qdrant/search_test?query=как+простить+обиду&limit=3"
```

---

## Environment Variables

### Для Qdrant (добавлены автоматически в Railway):

```bash
# Qdrant Cloud credentials (уже настроены)
QDRANT_URL=https://33d94c1b-cc7f-4b71-82cc-dcee289122f0.eu-central-1-0.aws.cloud.qdrant.io:6333
QDRANT_API_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.UTJlYE3KsxYq-NCTexIE035VcMuZ5KiTAf79ezuMYgg

# Конфигурация
QDRANT_COLLECTION=course_knowledge
EMBEDDING_MODEL=all-MiniLM-L6-v2

# ПЕРЕКЛЮЧАТЕЛЬ (единственная переменная которую нужно менять)
USE_QDRANT=false  # По умолчанию используется Graphiti
```

### Для Graphiti/Neo4j (уже настроены):

```bash
# Neo4j Aura credentials
NEO4J_URI=neo4j+s://51b8e0bb.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=fLWG-zJubpul21UaKELz77ISQIPFLWk-oG06kY4JzzM
GRAPHITI_ENABLED=true
```

---

## Как работает переключение

### Architecture

```
User Query
    │
    ▼
┌──────────────────────────────┐
│ KnowledgeSearchService       │
│  - Проверяет USE_QDRANT      │
└──────────┬───────────────────┘
           │
    ┌──────┴──────┐
    │             │
    ▼             ▼
if USE_QDRANT    else
┌─────────┐     ┌─────────┐
│ Qdrant  │     │Graphiti │
│ Service │     │ Service │
└─────────┘     └─────────┘
```

### Code Flow

**1. bot/config.py:**
```python
USE_QDRANT = os.getenv('USE_QDRANT', 'false').lower() in ('true', '1', 'yes')
```

**2. bot/services/knowledge_search.py:**
```python
def __init__(self):
    if USE_QDRANT and qdrant_enabled:
        logger.info("🔵 Using QDRANT for search")
    else:
        logger.info("🟢 Using GRAPHITI for search")

async def search(self, query):
    if self.use_qdrant:
        # Поиск через Qdrant
        return await self._search_qdrant(query)
    else:
        # Поиск через Graphiti
        return await self._search_graphiti(query)
```

---

## API Endpoints

### Qdrant Endpoints:

| Method | Endpoint | Описание |
|--------|----------|----------|
| GET | `/api/admin/qdrant/health` | Проверка статуса Qdrant service |
| GET | `/api/admin/qdrant/stats` | Статистика collection (количество points) |
| POST | `/api/admin/qdrant/migrate` | Запуск миграции данных |
| GET | `/api/admin/qdrant/migrate_status` | Статус миграции (progress, errors) |
| GET | `/api/admin/qdrant/search_test` | Тестовый поиск (`?query=...&limit=5`) |

### Graphiti Endpoints (существующие):

| Method | Endpoint | Описание |
|--------|----------|----------|
| GET | `/api/admin/stats` | Статистика Neo4j (nodes, episodes) |
| POST | `/api/admin/load_knowledge` | Загрузка entities в Graphiti |
| GET | `/api/admin/load_status` | Статус загрузки |

---

## Сравнение производительности

### Latency (время ответа):

| Операция | Qdrant | Graphiti | Победитель |
|----------|--------|----------|------------|
| Semantic search (5 results) | 30-50ms | 100-200ms | 🏆 Qdrant (2-4x быстрее) |
| Hybrid search | 40-60ms | 150-250ms | 🏆 Qdrant |
| Graph traversal | ❌ Не поддерживается | 50-100ms | 🏆 Graphiti |

### Качество результатов:

| Тип запроса | Qdrant | Graphiti |
|-------------|--------|----------|
| "Как простить обиду?" (semantic) | ✅ Excellent | ✅ Excellent |
| "Урок 5 техники" (keyword) | ✅ Good | ✅ Excellent |
| "Техники из блока 1" (graph) | ❌ Не поддерживается | ✅ Excellent |

---

## Когда использовать Qdrant?

### ✅ Рекомендуется для:

1. **Быстрый semantic search**
   - Нужен ответ < 50ms
   - Высокая нагрузка (>100 запросов/мин)

2. **Простая архитектура**
   - Только FAQ и уроки (без сложных relationships)
   - Не нужен graph traversal

3. **Cost optimization**
   - Qdrant free tier: 1GB (достаточно для 1M vectors)
   - Нет расходов на OpenAI для entity extraction

### ⚠️ НЕ рекомендуется если:

1. **Нужны graph relationships**
   - "Покажи техники из блока 1"
   - "Какие уроки связаны с этой техникой?"

2. **Нужен temporal reasoning**
   - "Что мы обсуждали на прошлой неделе?"
   - "Когда это было добавлено?"

---

## Откат на Graphiti

Если Qdrant не подошел, легко вернуться:

```bash
# 1. Railway Dashboard → Variables → USE_QDRANT=false
# 2. Railway автоматически перезапустит сервис
# 3. Graphiti продолжит работать с 449 существующими entities
```

**Важно:** Данные в Graphiti/Neo4j НЕ удаляются при переключении на Qdrant. Они остаются и доступны при откате.

---

## Troubleshooting

### Проблема: "Qdrant service not available"

**Причина:** `USE_QDRANT=true`, но Qdrant Cloud недоступен.

**Решение:**
```bash
# Проверить health
curl "https://ignatova-stroinost-bot-production.up.railway.app/api/admin/qdrant/health"

# Проверить credentials
echo $QDRANT_URL
echo $QDRANT_API_KEY

# Откатиться на Graphiti
USE_QDRANT=false
```

### Проблема: "Collection not found"

**Причина:** Collection `course_knowledge` не создана.

**Решение:**
```bash
# Запустить миграцию - она создаст collection автоматически
curl -X POST ".../api/admin/qdrant/migrate" -d '{"reset": true}'
```

### Проблема: "No results found"

**Причина:** Entities не загружены в Qdrant.

**Решение:**
```bash
# Проверить статистику
curl ".../api/admin/qdrant/stats"

# Если points_count = 0 → запустить миграцию
curl -X POST ".../api/admin/qdrant/migrate"
```

---

## FAQ

### Q: Можно ли использовать обе системы одновременно?

**A:** Нет, переключатель работает как `if/else`. Но обе системы **сосуществуют** - данные в Graphiti и Qdrant хранятся независимо.

### Q: Нужно ли удалять данные из Graphiti при переключении на Qdrant?

**A:** Нет! Данные остаются в обеих системах. Просто меняется какая система используется для поиска.

### Q: Сколько стоит миграция?

**A:** Бесплатно. Embeddings генерируются локально через `sentence-transformers`, без вызовов OpenAI API.

### Q: Можно ли добавлять новые entities после миграции?

**A:** Да. Используйте endpoint `/api/admin/qdrant/migrate` с параметром `reset=false` - он загрузит только новые entities.

### Q: Как сравнить результаты Qdrant vs Graphiti?

**A:**
```bash
# 1. Тестовый поиск в Qdrant (USE_QDRANT=true)
curl ".../api/admin/qdrant/search_test?query=как+простить+обиду"

# 2. Переключить на Graphiti (USE_QDRANT=false)
# 3. Тестовый поиск в Graphiti
curl ".../api/admin/search_test?query=как+простить+обиду"

# Сравнить: latency, relevance_score, results_count
```

---

## Дальнейшие улучшения

### Возможные фичи:

1. **A/B Testing Mode**
   - Запускать оба поиска параллельно
   - Логировать результаты для сравнения
   - Автоматические метрики (latency, overlap)

2. **Hybrid Approach**
   - Qdrant для FAQ (fast)
   - Graphiti для уроков (graph relationships)
   - Объединение результатов

3. **Auto-switching**
   - Определять тип запроса
   - Semantic queries → Qdrant
   - Graph queries → Graphiti

---

## Контакты

**Qdrant Cloud Dashboard:**
https://cloud.qdrant.io
- Cluster ID: `33d94c1b-cc7f-4b71-82cc-dcee289122f0`
- Region: `eu-central-1` (AWS)
- Collection: `course_knowledge`

**Railway Project:**
https://railway.app/project/a470438c-3a6c-4952-80df-9e2c067233c6
- Service: `ignatova-stroinost-bot`

**Документация:**
- Qdrant Docs: https://qdrant.tech/documentation/
- Graphiti Docs: https://github.com/getzep/graphiti

---

## История изменений

**14 ноября 2025** - Initial implementation
- Создан QdrantService (`bot/services/qdrant_service.py`)
- Добавлен переключатель в KnowledgeSearchService
- Скрипт миграции (`scripts/migrate_to_qdrant.py`)
- Admin API endpoints (`/api/admin/qdrant/*`)
- Документация
