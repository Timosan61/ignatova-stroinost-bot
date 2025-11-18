# План улучшения text-embedding-3-small для systemd deployment

**Дата создания:** 18 ноября 2025
**Статус:** В планах (не реализовано)
**Приоритет:** HIGH
**Общее время:** 6-9 часов работы

---

## 🎯 Цели и мотивация

### Проблемы текущей реализации:
1. **Качество поиска:** Только semantic search (без keyword matching)
2. **Мониторинг:** Minimal visibility в production (нет метрик latency, tokens, costs)
3. **Скорость:** Нет batch processing, нет caching повторных queries, последовательная обработка

### Цели после улучшений:
- ✅ **Качество:** +15-25% точность через Hybrid Search (semantic + fulltext)
- ✅ **Мониторинг:** Full visibility (latency, tokens, costs) для production debugging
- ✅ **Скорость:** 4-5x быстрее миграции, 127x быстрее повторные queries, 2x быстрее multi-stage search

---

## 📋 Этапы внедрения

### Этап 1: Hybrid Search в Supabase
**Время:** 2-3 часа
**Приоритет:** 🔥 HIGH
**Эффект:** +15-25% точность поиска

#### Что делаем:

**1.1. SQL Migration - Hybrid Search Function**

Создать файл: `migrations/supabase/hybrid_search.sql`

```sql
-- Функция для hybrid search (semantic + fulltext)
CREATE OR REPLACE FUNCTION match_documents_hybrid(
    query_embedding vector(1536),
    query_text text,
    entity_filter text DEFAULT NULL,
    match_threshold float DEFAULT 0.7,
    match_count int DEFAULT 10,
    semantic_weight float DEFAULT 0.7,
    fulltext_weight float DEFAULT 0.3
)
RETURNS TABLE (
    id uuid,
    content text,
    metadata jsonb,
    entity_type text,
    similarity float,
    fulltext_rank float,
    combined_score float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    WITH semantic_results AS (
        -- Semantic search через pgvector
        SELECT
            ck.id,
            ck.content,
            ck.metadata,
            ck.metadata->>'entity_type' as entity_type,
            1 - (ck.embedding <=> query_embedding) as similarity,
            0.0 as fulltext_rank
        FROM course_knowledge ck
        WHERE
            (entity_filter IS NULL OR ck.metadata->>'entity_type' = entity_filter)
            AND 1 - (ck.embedding <=> query_embedding) > match_threshold
        ORDER BY ck.embedding <=> query_embedding
        LIMIT match_count * 2
    ),
    fulltext_results AS (
        -- Fulltext search через tsvector
        SELECT
            ck.id,
            ck.content,
            ck.metadata,
            ck.metadata->>'entity_type' as entity_type,
            0.0 as similarity,
            ts_rank(to_tsvector('russian', ck.content), plainto_tsquery('russian', query_text)) as fulltext_rank
        FROM course_knowledge ck
        WHERE
            (entity_filter IS NULL OR ck.metadata->>'entity_type' = entity_filter)
            AND to_tsvector('russian', ck.content) @@ plainto_tsquery('russian', query_text)
        ORDER BY fulltext_rank DESC
        LIMIT match_count * 2
    ),
    combined AS (
        -- Объединяем результаты с RRF (Reciprocal Rank Fusion)
        SELECT
            COALESCE(s.id, f.id) as id,
            COALESCE(s.content, f.content) as content,
            COALESCE(s.metadata, f.metadata) as metadata,
            COALESCE(s.entity_type, f.entity_type) as entity_type,
            COALESCE(s.similarity, 0.0) as similarity,
            COALESCE(f.fulltext_rank, 0.0) as fulltext_rank,
            (COALESCE(s.similarity, 0.0) * semantic_weight +
             COALESCE(f.fulltext_rank, 0.0) * fulltext_weight) as combined_score
        FROM semantic_results s
        FULL OUTER JOIN fulltext_results f ON s.id = f.id
    )
    SELECT * FROM combined
    ORDER BY combined_score DESC
    LIMIT match_count;
END;
$$;

-- Создаём GIN индекс для fulltext search
CREATE INDEX IF NOT EXISTS idx_course_knowledge_content_fulltext
ON course_knowledge USING GIN (to_tsvector('russian', content));
```

**1.2. Обновить `bot/services/supabase_service.py`**

Добавить метод `hybrid_search()`:

```python
async def hybrid_search(
    self,
    query: str,
    entity_type: Optional[str] = None,
    limit: int = 10,
    semantic_weight: float = 0.7,
    fulltext_weight: float = 0.3
) -> List[Dict[str, Any]]:
    """
    Hybrid search: semantic + fulltext

    Args:
        query: Поисковый запрос
        entity_type: Фильтр по типу (lesson, correction, faq, question, brainwrite)
        limit: Количество результатов
        semantic_weight: Вес semantic search (0-1)
        fulltext_weight: Вес fulltext search (0-1)

    Returns:
        List результатов с combined_score
    """
    try:
        # Генерируем embedding для query
        query_embedding = self._generate_embedding(query)

        # Вызываем hybrid search function
        response = await self.supabase.rpc(
            'match_documents_hybrid',
            {
                'query_embedding': query_embedding,
                'query_text': query,
                'entity_filter': entity_type,
                'match_threshold': 0.7,
                'match_count': limit,
                'semantic_weight': semantic_weight,
                'fulltext_weight': fulltext_weight
            }
        ).execute()

        results = []
        for item in response.data:
            results.append({
                'content': item['content'],
                'metadata': item['metadata'],
                'entity_type': item['entity_type'],
                'score': item['combined_score'],
                'semantic_score': item['similarity'],
                'fulltext_score': item['fulltext_rank'],
                'source': 'supabase_hybrid'
            })

        logger.info(f"✅ Hybrid search: {len(results)} results, avg_score={sum(r['score'] for r in results)/len(results) if results else 0:.2f}")
        return results

    except Exception as e:
        logger.error(f"❌ Hybrid search failed: {e}")
        # Fallback на обычный semantic search
        return await self.search_semantic(query, entity_type, limit)
```

**1.3. Обновить `bot/services/knowledge_search.py`**

Заменить `search_semantic()` на `hybrid_search()` в методе `_search_semantic()`:

```python
async def _search_semantic(self, query: str, limit: int) -> List[Dict]:
    """Multi-stage hybrid search с приоритетами"""
    all_results = []

    # ЭТАП 1: Lessons (ПРИОРИТЕТ 1) - boost 1.5x
    if self.use_supabase and self.supabase_service:
        lesson_results = await self.supabase_service.hybrid_search(
            query=query,
            entity_type="lesson",
            limit=limit,
            semantic_weight=0.7,
            fulltext_weight=0.3
        )
        for r in lesson_results:
            r['score'] = r['score'] * 1.5  # BOOST!
            all_results.append(r)

    # ЭТАП 2: Corrections (ПРИОРИТЕТ 2) - boost 1.2x
    if len(all_results) < limit:
        correction_results = await self.supabase_service.hybrid_search(
            query=query,
            entity_type="correction",
            limit=limit,
            semantic_weight=0.7,
            fulltext_weight=0.3
        )
        for r in correction_results:
            r['score'] = r['score'] * 1.2
            all_results.append(r)

    # ЭТАП 3: FAQ (ПРИОРИТЕТ 3) - no boost
    if len(all_results) < limit:
        faq_results = await self.supabase_service.hybrid_search(
            query=query,
            entity_type="faq",
            limit=limit
        )
        all_results.extend(faq_results)

    # Сортируем по boosted score
    all_results.sort(key=lambda x: x['score'], reverse=True)
    return all_results[:limit]
```

---

### Этап 2: Comprehensive Monitoring
**Время:** 1-2 часа
**Приоритет:** 🔥 HIGH
**Эффект:** Full visibility в production

#### Что делаем:

**2.1. Создать `bot/monitoring/embedding_monitor.py`**

```python
"""
Monitoring и метрики для embeddings (OpenAI text-embedding-3-small)
"""
import time
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)

@dataclass
class EmbeddingMetrics:
    """Метрики для tracking embeddings"""

    # Counters
    total_calls: int = 0
    total_tokens: int = 0
    total_cost_usd: float = 0.0

    # Latency tracking
    latencies: List[float] = field(default_factory=list)

    # Errors
    errors: int = 0

    # Session info
    session_start: datetime = field(default_factory=datetime.now)

    def add_call(self, tokens: int, latency_ms: float, cost_usd: float):
        """Добавить метрики одного вызова"""
        self.total_calls += 1
        self.total_tokens += tokens
        self.total_cost_usd += cost_usd
        self.latencies.append(latency_ms)

        # Логируем каждый вызов
        logger.info(
            f"⏱️ OpenAI embedding: {latency_ms:.1f}ms | "
            f"tokens={tokens} | "
            f"cost=${cost_usd:.7f} | "
            f"model=text-embedding-3-small"
        )

    def add_error(self):
        """Зарегистрировать ошибку"""
        self.errors += 1

    @property
    def avg_latency_ms(self) -> float:
        """Средняя latency в миллисекундах"""
        return sum(self.latencies) / len(self.latencies) if self.latencies else 0.0

    @property
    def p95_latency_ms(self) -> float:
        """95-й перцентиль latency"""
        if not self.latencies:
            return 0.0
        sorted_latencies = sorted(self.latencies)
        idx = int(len(sorted_latencies) * 0.95)
        return sorted_latencies[idx]

    @property
    def session_duration_minutes(self) -> float:
        """Длительность сессии в минутах"""
        return (datetime.now() - self.session_start).total_seconds() / 60

    def summary(self) -> Dict:
        """Получить summary статистику"""
        return {
            "total_calls": self.total_calls,
            "total_tokens": self.total_tokens,
            "total_cost_usd": round(self.total_cost_usd, 6),
            "avg_latency_ms": round(self.avg_latency_ms, 1),
            "p95_latency_ms": round(self.p95_latency_ms, 1),
            "errors": self.errors,
            "session_duration_minutes": round(self.session_duration_minutes, 1),
            "calls_per_minute": round(self.total_calls / self.session_duration_minutes, 2) if self.session_duration_minutes > 0 else 0,
            "avg_tokens_per_call": round(self.total_tokens / self.total_calls, 1) if self.total_calls > 0 else 0
        }

    def log_summary(self):
        """Логировать summary"""
        summary = self.summary()
        logger.info(
            f"\n📊 Embedding Session Stats:\n"
            f"  Calls: {summary['total_calls']:,}\n"
            f"  Tokens: {summary['total_tokens']:,}\n"
            f"  Cost: ${summary['total_cost_usd']:.6f}\n"
            f"  Avg Latency: {summary['avg_latency_ms']}ms\n"
            f"  P95 Latency: {summary['p95_latency_ms']}ms\n"
            f"  Errors: {summary['errors']}\n"
            f"  Duration: {summary['session_duration_minutes']} min\n"
            f"  Rate: {summary['calls_per_minute']} calls/min"
        )

# Глобальный singleton для метрик
_global_metrics = EmbeddingMetrics()

def get_metrics() -> EmbeddingMetrics:
    """Получить глобальные метрики"""
    return _global_metrics

def reset_metrics():
    """Сбросить метрики (для тестов)"""
    global _global_metrics
    _global_metrics = EmbeddingMetrics()
```

**2.2. Обновить `bot/services/supabase_service.py`**

Добавить monitoring в `_generate_embedding()`:

```python
from bot.monitoring.embedding_monitor import get_metrics
import time

def _generate_embedding(self, text: str) -> List[float]:
    """Генерация embedding через OpenAI API с monitoring"""
    try:
        start_time = time.time()

        response = self.openai_client.embeddings.create(
            input=text,
            model=self.embedding_model
        )

        latency_ms = (time.time() - start_time) * 1000
        tokens = response.usage.total_tokens

        # Стоимость text-embedding-3-small: $0.00002 за 1K tokens
        cost_usd = (tokens / 1000) * 0.00002

        # Записываем метрики
        metrics = get_metrics()
        metrics.add_call(tokens=tokens, latency_ms=latency_ms, cost_usd=cost_usd)

        return response.data[0].embedding

    except Exception as e:
        logger.error(f"❌ Embedding generation failed: {e}")
        get_metrics().add_error()
        raise
```

**2.3. Добавить API endpoint в `main.py`**

```python
from bot.monitoring.embedding_monitor import get_metrics

@app.get("/api/admin/embedding/stats")
async def embedding_stats():
    """Получить статистику embeddings"""
    metrics = get_metrics()
    return {
        "status": "ok",
        "embedding_model": "text-embedding-3-small",
        "metrics": metrics.summary()
    }
```

**2.4. Добавить в systemd service**

Обновить `~/.config/systemd/user/ignatova-bot.service`:

```ini
[Service]
# Structured logging для journalctl
Environment="PYTHONUNBUFFERED=1"
Environment="EMBEDDING_MONITORING_ENABLED=true"

# Логируем метрики каждые 5 минут
ExecStartPost=/bin/sh -c 'while true; do sleep 300; curl -s http://localhost:8001/api/admin/embedding/stats | jq; done'
```

---

### Этап 3: Batch Processing
**Время:** 1 час
**Приоритет:** 🟡 MEDIUM
**Эффект:** Миграции в 4-5x быстрее

#### Что делаем:

**3.1. Обновить `bot/services/supabase_service.py`**

Добавить batch метод:

```python
def _generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
    """
    Batch генерация embeddings (до 100 текстов за раз)

    Экономия:
    - Network overhead: N requests → 1 request
    - Cost: то же самое (платим за токены)
    - Time: ~4-5x быстрее для миграций
    """
    try:
        start_time = time.time()

        response = self.openai_client.embeddings.create(
            input=texts,  # List[str] - до 100 items
            model=self.embedding_model
        )

        latency_ms = (time.time() - start_time) * 1000
        tokens = response.usage.total_tokens
        cost_usd = (tokens / 1000) * 0.00002

        # Метрики для batch call
        metrics = get_metrics()
        metrics.add_call(tokens=tokens, latency_ms=latency_ms, cost_usd=cost_usd)

        logger.info(
            f"✅ Batch embeddings: {len(texts)} texts, "
            f"{latency_ms:.0f}ms, "
            f"{tokens} tokens, "
            f"${cost_usd:.6f}"
        )

        return [item.embedding for item in response.data]

    except Exception as e:
        logger.error(f"❌ Batch embedding failed: {e}")
        get_metrics().add_error()
        raise
```

**3.2. Обновить `scripts/migrate_to_supabase.py`**

Заменить цикл на batch processing:

```python
# ДО: последовательно (22 минуты для 3,234 entities)
for entity in entities:
    embedding = self._generate_embedding(entity['content'])
    # ...
    time.sleep(0.05)  # Rate limiting

# ПОСЛЕ: батчами (5 минут для 3,234 entities)
BATCH_SIZE = 100  # OpenAI limit

for i in range(0, len(entities), BATCH_SIZE):
    batch = entities[i:i+BATCH_SIZE]
    texts = [e['content'] for e in batch]

    # Генерируем batch embeddings
    embeddings = self._generate_embeddings_batch(texts)

    # Загружаем в Supabase
    for entity, embedding in zip(batch, embeddings):
        await self.supabase.table('course_knowledge').insert({
            'content': entity['content'],
            'metadata': entity['metadata'],
            'embedding': embedding
        }).execute()

    # Rate limiting между батчами
    time.sleep(0.5)  # 500ms между батчами
```

---

### Этап 4: Query Caching
**Время:** 1-2 часа
**Приоритет:** 🟡 MEDIUM
**Эффект:** Повторные queries 127x быстрее

#### Что делаем:

**4.1. Создать `bot/cache/embedding_cache.py`**

```python
"""
LRU Cache для embeddings queries
"""
from functools import lru_cache
from typing import List, Optional
import hashlib
import time
import logging

logger = logging.getLogger(__name__)

class EmbeddingCache:
    """
    In-memory LRU cache для embeddings

    Кэшируем пары (query_text -> embedding_vector)
    TTL: 1 час (3600 секунд)
    """

    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.cache = {}  # {query_hash: (embedding, timestamp)}
        self.hits = 0
        self.misses = 0

    def _get_hash(self, text: str) -> str:
        """Получить hash для текста"""
        return hashlib.sha256(text.encode()).hexdigest()[:16]

    def get(self, text: str) -> Optional[List[float]]:
        """Получить embedding из cache"""
        key = self._get_hash(text)

        if key in self.cache:
            embedding, timestamp = self.cache[key]

            # Проверяем TTL
            if time.time() - timestamp < self.ttl_seconds:
                self.hits += 1
                logger.debug(f"✅ Cache HIT: {text[:50]}...")
                return embedding
            else:
                # Expired
                del self.cache[key]
                logger.debug(f"⏰ Cache EXPIRED: {text[:50]}...")

        self.misses += 1
        logger.debug(f"❌ Cache MISS: {text[:50]}...")
        return None

    def set(self, text: str, embedding: List[float]):
        """Сохранить embedding в cache"""
        key = self._get_hash(text)

        # LRU eviction если превышен лимит
        if len(self.cache) >= self.max_size:
            # Удаляем самый старый
            oldest_key = min(self.cache.items(), key=lambda x: x[1][1])[0]
            del self.cache[oldest_key]
            logger.debug(f"🗑️ Cache EVICT: {oldest_key}")

        self.cache[key] = (embedding, time.time())
        logger.debug(f"💾 Cache SET: {text[:50]}...")

    @property
    def hit_rate(self) -> float:
        """Cache hit rate (0-1)"""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    def stats(self) -> dict:
        """Статистика cache"""
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": round(self.hit_rate * 100, 1),
            "ttl_seconds": self.ttl_seconds
        }

# Глобальный singleton
_global_cache = None

def get_cache() -> EmbeddingCache:
    """Получить глобальный cache"""
    global _global_cache
    if _global_cache is None:
        _global_cache = EmbeddingCache(max_size=1000, ttl_seconds=3600)
    return _global_cache
```

**4.2. Обновить `bot/services/supabase_service.py`**

Добавить caching в `_generate_embedding()`:

```python
from bot.cache.embedding_cache import get_cache

def _generate_embedding(self, text: str) -> List[float]:
    """Генерация embedding с caching"""
    cache = get_cache()

    # Проверяем cache
    cached_embedding = cache.get(text)
    if cached_embedding is not None:
        return cached_embedding

    # Cache miss - генерируем через OpenAI
    try:
        start_time = time.time()

        response = self.openai_client.embeddings.create(
            input=text,
            model=self.embedding_model
        )

        latency_ms = (time.time() - start_time) * 1000
        tokens = response.usage.total_tokens
        cost_usd = (tokens / 1000) * 0.00002

        metrics = get_metrics()
        metrics.add_call(tokens=tokens, latency_ms=latency_ms, cost_usd=cost_usd)

        embedding = response.data[0].embedding

        # Сохраняем в cache
        cache.set(text, embedding)

        return embedding

    except Exception as e:
        logger.error(f"❌ Embedding generation failed: {e}")
        get_metrics().add_error()
        raise
```

**4.3. Добавить API endpoint**

```python
from bot.cache.embedding_cache import get_cache

@app.get("/api/admin/embedding/cache")
async def embedding_cache_stats():
    """Статистика embedding cache"""
    cache = get_cache()
    return {
        "status": "ok",
        "cache": cache.stats()
    }
```

**4.4. Конфигурация в `.env`**

```bash
# Embedding Cache
EMBEDDING_CACHE_ENABLED=true
EMBEDDING_CACHE_SIZE=1000
EMBEDDING_CACHE_TTL=3600
```

---

### Этап 5: Async Parallel Processing
**Время:** 1 час
**Приоритет:** 🟢 LOW
**Эффект:** Multi-stage search 2x быстрее

#### Что делаем:

**5.1. Рефакторинг на async/await**

Обновить `bot/services/supabase_service.py`:

```python
async def _generate_embedding_async(self, text: str) -> List[float]:
    """Async версия для параллельных calls"""
    # Используем asyncio.to_thread для blocking OpenAI call
    import asyncio

    return await asyncio.to_thread(self._generate_embedding, text)
```

**5.2. Параллельная обработка в `knowledge_search.py`**

```python
async def _search_semantic(self, query: str, limit: int) -> List[Dict]:
    """Multi-stage search с параллельными embedding calls"""
    import asyncio

    # Генерируем embedding только один раз (не три!)
    query_embedding = await self.supabase_service._generate_embedding_async(query)

    # Параллельно ищем во всех категориях
    lesson_task = self.supabase_service.hybrid_search(
        query=query, entity_type="lesson", limit=limit
    )
    correction_task = self.supabase_service.hybrid_search(
        query=query, entity_type="correction", limit=limit
    )
    faq_task = self.supabase_service.hybrid_search(
        query=query, entity_type="faq", limit=limit
    )

    # Ждём все результаты одновременно
    lesson_results, correction_results, faq_results = await asyncio.gather(
        lesson_task, correction_task, faq_task
    )

    # Применяем boosting
    for r in lesson_results:
        r['score'] *= 1.5
    for r in correction_results:
        r['score'] *= 1.2

    # Объединяем и сортируем
    all_results = lesson_results + correction_results + faq_results
    all_results.sort(key=lambda x: x['score'], reverse=True)

    return all_results[:limit]
```

**Эффект:**
- ДО: 3 последовательных search calls = 300ms
- ПОСЛЕ: 1 параллельный batch = 150ms

---

### Этап 6: systemd Service Optimization
**Время:** 30 минут
**Приоритет:** 🟢 LOW
**Эффект:** Production-ready configuration

#### Что делаем:

**6.1. Обновить `~/.config/systemd/user/ignatova-bot.service`**

```ini
[Unit]
Description=Ignatova Stroinost Bot (Telegram + Supabase)
After=network.target ignatova-bot-ngrok.service
Requires=ignatova-bot-ngrok.service

[Service]
Type=simple
WorkingDirectory=/home/coder/projects/bot_cloning_railway/clones/ignatova-stroinost-bot
EnvironmentFile=/home/coder/projects/bot_cloning_railway/clones/ignatova-stroinost-bot/.env

# OpenAI API (для embeddings)
Environment="OPENAI_API_KEY=sk-proj-..."
Environment="OPENAI_EMBEDDING_MODEL=text-embedding-3-small"

# Supabase
Environment="USE_SUPABASE=true"
Environment="SUPABASE_URL=https://..."
Environment="SUPABASE_SERVICE_KEY=..."

# Embedding Optimization
Environment="EMBEDDING_CACHE_ENABLED=true"
Environment="EMBEDDING_CACHE_SIZE=1000"
Environment="EMBEDDING_CACHE_TTL=3600"
Environment="EMBEDDING_MONITORING_ENABLED=true"

# Logging
Environment="PYTHONUNBUFFERED=1"
StandardOutput=journal
StandardError=journal

# Service
ExecStart=/usr/bin/python3 main.py
Restart=always
RestartSec=10

# Health check каждые 5 минут
ExecStartPost=/bin/sh -c 'while sleep 300; do curl -s http://localhost:8001/api/admin/embedding/stats | jq ".metrics"; done'

[Install]
WantedBy=default.target
```

**6.2. Health Check Endpoints**

```python
# main.py

@app.get("/health/embeddings")
async def health_embeddings():
    """Health check для embedding service"""
    try:
        # Тестовый embedding call
        test_text = "test"
        service = get_supabase_service()
        embedding = service._generate_embedding(test_text)

        return {
            "status": "healthy",
            "model": "text-embedding-3-small",
            "embedding_dimensions": len(embedding),
            "cache": get_cache().stats(),
            "metrics": get_metrics().summary()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }
```

---

## 📊 Ожидаемые результаты

### Metrics Comparison

| Метрика | До улучшений | После улучшений | Улучшение |
|---------|--------------|-----------------|-----------|
| **Точность поиска** | Baseline | +15-25% | Hybrid Search |
| **Search latency (single)** | 100-250ms | 100-250ms | Без изменений |
| **Search latency (multi-stage)** | 300ms | 150ms | **2x быстрее** |
| **Migration time (3,234)** | 22 мин | ~5 мин | **4.4x быстрее** |
| **Повторные queries** | 127ms | <1ms | **127x быстрее** |
| **Cache hit rate** | 0% | ~35% | Новая фича |
| **OpenAI API costs** | Baseline | -30-40% | Cache savings |
| **Monitoring** | Minimal | Full metrics | Production-ready |

### Cost Analysis

**Текущие costs (до улучшений):**
- Migration: $0.02 (one-time)
- 10,000 queries/month: $0.24/year
- Total: <$1/year

**После улучшений (с caching):**
- Migration: $0.02 (one-time, но 4x быстрее)
- 10,000 queries/month: $0.15/year (cache hit 35%)
- Total: ~$0.60/year

**Экономия:** $0.40/year + 4x быстрее миграции

---

## 🗂️ Файлы для создания/изменения

### Новые файлы:

| Файл | Размер | Описание |
|------|--------|----------|
| `bot/monitoring/embedding_monitor.py` | ~150 lines | Метрики и мониторинг |
| `bot/cache/embedding_cache.py` | ~120 lines | LRU cache для queries |
| `migrations/supabase/hybrid_search.sql` | ~80 lines | SQL function для hybrid search |
| `docs/EMBEDDING_OPTIMIZATION_PLAN.md` | ~1,200 lines | Этот файл |

### Изменённые файлы:

| Файл | Изменения | Строки |
|------|-----------|--------|
| `bot/services/supabase_service.py` | +hybrid_search(), +monitoring, +batch, +cache | +150 |
| `bot/services/knowledge_search.py` | Интеграция hybrid search, async | +50 |
| `scripts/migrate_to_supabase.py` | Batch processing | +30 |
| `main.py` | +API endpoints для metrics | +30 |
| `~/.config/systemd/user/ignatova-bot.service` | Environment variables | +10 |

**Total:** ~500 новых строк кода

---

## 🚀 Порядок внедрения

### Quick Wins (День 1: 2-3 часа):

✅ **Этап 2: Monitoring** (1-2 часа)
- Создать `embedding_monitor.py`
- Добавить метрики в `supabase_service.py`
- API endpoint `/api/admin/embedding/stats`

✅ **Этап 3: Batch Processing** (1 час)
- Метод `_generate_embeddings_batch()`
- Обновить `migrate_to_supabase.py`

**Результат:** Full visibility + 4x быстрее миграции

---

### Main Features (День 2: 3-4 часа):

✅ **Этап 1: Hybrid Search** (2-3 часа)
- SQL migration `hybrid_search.sql`
- Метод `hybrid_search()` в `supabase_service.py`
- Интеграция в `knowledge_search.py`

✅ **Этап 4: Query Caching** (1-2 часа)
- Создать `embedding_cache.py`
- Интеграция в `_generate_embedding()`
- API endpoint `/api/admin/embedding/cache`

**Результат:** +15-25% точность + 127x быстрее повторные queries

---

### Optimizations (День 3: 1-2 часа, опционально):

⚠️ **Этап 5: Async Parallel** (1 час)
- Рефакторинг на async/await
- Параллельные embedding calls

⚠️ **Этап 6: systemd Service** (30 мин)
- Обновить `.service` файл
- Health check endpoints
- Документация

**Результат:** 2x быстрее multi-stage search

---

## 📝 Checklist для внедрения

### Pre-deployment:

- [ ] Создать ветку `feature/embedding-optimization`
- [ ] Backup текущей БД Supabase
- [ ] Проверить .env переменные

### Этап 1 (Hybrid Search):

- [ ] Создать `migrations/supabase/hybrid_search.sql`
- [ ] Применить миграцию в Supabase Dashboard
- [ ] Создать GIN индекс для fulltext search
- [ ] Обновить `bot/services/supabase_service.py` (+hybrid_search)
- [ ] Обновить `bot/services/knowledge_search.py` (интеграция)
- [ ] Тестировать локально

### Этап 2 (Monitoring):

- [ ] Создать `bot/monitoring/embedding_monitor.py`
- [ ] Добавить метрики в `supabase_service.py`
- [ ] Создать API endpoint `/api/admin/embedding/stats`
- [ ] Тестировать метрики

### Этап 3 (Batch Processing):

- [ ] Добавить `_generate_embeddings_batch()` в `supabase_service.py`
- [ ] Обновить `scripts/migrate_to_supabase.py`
- [ ] Протестировать batch миграцию

### Этап 4 (Caching):

- [ ] Создать `bot/cache/embedding_cache.py`
- [ ] Интегрировать в `_generate_embedding()`
- [ ] Создать API endpoint `/api/admin/embedding/cache`
- [ ] Тестировать cache hit rate

### Этап 5 (Async):

- [ ] Рефакторинг на async/await
- [ ] Параллельные embedding calls в `knowledge_search.py`
- [ ] Тестировать latency improvement

### Этап 6 (systemd):

- [ ] Обновить `~/.config/systemd/user/ignatova-bot.service`
- [ ] Добавить health check endpoints
- [ ] Reload systemd daemon: `systemctl --user daemon-reload`
- [ ] Restart service: `systemctl --user restart ignatova-bot.service`
- [ ] Проверить логи: `journalctl --user -u ignatova-bot.service -f`

### Post-deployment:

- [ ] Мониторить метрики 24 часа
- [ ] Проверить cache hit rate
- [ ] Обновить `CLAUDE.md` с новой информацией
- [ ] Создать `docs/EMBEDDING_OPTIMIZATION.md` (summary)
- [ ] Commit в GitHub
- [ ] Опционально: Deploy на Railway

---

## 🔍 Debugging & Troubleshooting

### Проверка hybrid search:

```bash
# Тестовый запрос
curl -X POST "http://localhost:8001/api/admin/test/hybrid_search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "как составить мозгоритм",
    "entity_type": "lesson",
    "limit": 5
  }'
```

### Проверка метрик:

```bash
# Embedding stats
curl "http://localhost:8001/api/admin/embedding/stats" | jq

# Cache stats
curl "http://localhost:8001/api/admin/embedding/cache" | jq

# Health check
curl "http://localhost:8001/health/embeddings" | jq
```

### systemd логи:

```bash
# Все логи
journalctl --user -u ignatova-bot.service -f

# Только embedding метрики
journalctl --user -u ignatova-bot.service -f | grep "OpenAI embedding"

# Summary stats
journalctl --user -u ignatova-bot.service -f | grep "Embedding Session Stats"
```

---

## 💡 Future Enhancements (не в этом плане)

### Дополнительные оптимизации:

1. **Cohere Reranking** (+10-15% точность, но $1/1K requests)
2. **Redis persistent cache** (сохранение между restarts)
3. **Prometheus metrics** (для Grafana dashboards)
4. **A/B testing framework** (сравнение hybrid vs semantic)
5. **Adaptive semantic/fulltext weights** (ML-based optimization)
6. **Query intent classification** (автовыбор semantic_weight/fulltext_weight)

### Advanced features:

7. **Multi-language support** (русский + английский tsvector)
8. **Phrase boosting** ("мозгоритм" → higher weight)
9. **Entity-specific weights** (lessons vs corrections разные веса)
10. **User feedback loop** (улучшение на основе кликов)

---

## 📚 Дополнительная информация

### Документация:

- **awesome-llm-apps:** https://github.com/Shubhamsaboo/awesome-llm-apps/tree/main/rag_tutorials
- **OpenAI Embeddings:** https://platform.openai.com/docs/guides/embeddings
- **Supabase Vector:** https://supabase.com/docs/guides/ai/vector-columns
- **pgvector:** https://github.com/pgvector/pgvector
- **PostgreSQL FTS:** https://www.postgresql.org/docs/current/textsearch.html

### Инспирация из awesome-llm-apps:

- **Agentic RAG GPT-5:** Agno framework, LanceDB, streaming
- **Corrective RAG:** Self-grading, query transformation, web fallback
- **Hybrid Search RAG:** Semantic + Keyword + BM25 + Reranking

### Текущая архитектура (reference):

- **Суммарно entities:** 3,234 (FAQ: 25, Lessons: 127, Corrections: 275, Questions: 2,635, Brainwrites: 172)
- **Embedding model:** text-embedding-3-small (1536D)
- **Vector DB:** Supabase (PostgreSQL + pgvector)
- **Миграция cost:** $0.02 (992,051 tokens)
- **Миграция time:** 22 минуты

---

**Статус:** ✅ План готов к реализации
**Дата:** 18 ноября 2025
**Автор:** Claude Code
**Версия:** 1.0
