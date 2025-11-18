# Требования к загрузке данных в Qdrant Vector Database

Полное руководство по форматам данных, требованиям API и частым ошибкам при миграции базы знаний в Qdrant.

---

## 📋 Содержание

1. [Обзор Qdrant](#обзор-qdrant)
2. [Требования к форматам данных](#требования-к-форматам-данных)
3. [История исправлений ошибок](#история-исправлений-ошибок)
4. [Структура Entity](#структура-entity)
5. [Процесс миграции](#процесс-миграции)
6. [Примеры кода](#примеры-кода)
7. [Troubleshooting](#troubleshooting)

---

## Обзор Qdrant

**Qdrant** - облачная векторная база данных для semantic search.

| Параметр | Значение |
|----------|----------|
| Cluster ID | `33d94c1b-cc7f-4b71-82cc-dcee289122f0` |
| Endpoint | `https://33d94c1b-cc7f-4b71-82cc-dcee289122f0.eu-central-1-0.aws.cloud.qdrant.io:6333` |
| Region | `eu-central-1` (AWS) |
| Collection | `course_knowledge` |
| Vector Size | 384 (all-MiniLM-L6-v2) |
| Distance Metric | COSINE |

---

## Требования к форматам данных

### 1. Point ID Format (КРИТИЧНО!)

**❌ НЕПРАВИЛЬНО:**
```python
entity = {
    "id": "faq_123",              # String ID - REJECTED!
    "id": f"lesson_{lesson_id}",  # String ID - REJECTED!
    "id": f"question_{idx}"       # String ID - REJECTED!
}
```

**✅ ПРАВИЛЬНО:**
```python
entity = {
    "id": 123,                    # Integer ID - ACCEPTED
    "id": entity_id,              # Integer variable - ACCEPTED
}
```

**Ошибка при неправильном формате:**
```json
{
  "status": {
    "error": "Format error in JSON body: value question_600 is not a valid point ID,
              valid values are either an unsigned integer or a UUID"
  }
}
```

**Требования Qdrant:**
- Point ID должен быть **unsigned integer** (0, 1, 2, ...) ИЛИ UUID
- String IDs **НЕ поддерживаются**
- Нельзя использовать префиксы типа `"faq_"`, `"lesson_"`

---

### 2. Vector Format

**Требования:**
```python
# Vector должен быть list of floats
vector = encoder.encode(text).tolist()  # ✅ Правильно

# Размер вектора
len(vector) == 384  # Для модели all-MiniLM-L6-v2
```

**Пример:**
```python
from sentence_transformers import SentenceTransformer

encoder = SentenceTransformer('all-MiniLM-L6-v2')
text = "Как простить обиду?"
vector = encoder.encode(text).tolist()

# vector = [0.123, -0.456, 0.789, ...] (384 floats)
```

---

### 3. Payload Structure

**Обязательные поля:**
```python
payload = {
    "entity_type": str,   # Тип entity (faq, lesson, correction, etc.)
    "title": str,         # Заголовок (макс. 100 символов)
    "content": str,       # Полный контент для поиска
    "metadata": dict,     # Дополнительные поля (optional)
    "created_at": str     # ISO timestamp
}
```

**Пример:**
```python
payload = {
    "entity_type": "faq",
    "title": "Вес встал, не уходит. Что делать?",
    "content": "FAQ (ЧАСТЫЙ ВОПРОС)\n\nQ: Вес встал...\n\nA: Остановка веса...",
    "metadata": {
        "category": "ПИТАНИЕ И ПИЩЕВОЕ ПОВЕДЕНИЕ",
        "keywords": ["мозгоритм", "встал", "вторичные"],
        "frequency": null
    },
    "created_at": "2025-11-14T17:10:37.770101"
}
```

---

### 4. Point Structure (Final)

**Финальная структура для upload:**
```python
from qdrant_client.models import PointStruct

point = PointStruct(
    id=0,                          # Integer ID
    vector=[0.123, -0.456, ...],   # 384 floats
    payload={
        "entity_type": "faq",
        "title": "...",
        "content": "...",
        "metadata": {...},
        "created_at": "2025-11-14T..."
    }
)
```

---

## История исправлений ошибок

### Error 1: AttributeError - FAQEntry.importance

**Commit:** ed90ee8

**Проблема:**
```python
# ❌ ОШИБКА
"metadata": {
    "frequency": faq.importance  # AttributeError: 'FAQEntry' object has no attribute 'importance'
}
```

**Исправление:**
```python
# ✅ ИСПРАВЛЕНО
"metadata": {
    "frequency": faq.frequency
}
```

**Файл:** `scripts/migrate_to_qdrant.py:187`

---

### Error 2: AttributeError - parse_curator_corrections

**Commit:** 9da27f9

**Проблема:**
```python
# ❌ ОШИБКА
corrections = parser.parse_curator_corrections(corrections_file)  # Method doesn't exist
```

**Исправление:**
```python
# ✅ ИСПРАВЛЕНО
corrections = parser.parse_corrections(corrections_file)
```

**Файл:** `scripts/migrate_to_qdrant.py:223`

---

### Error 3: Missing Files (*.gitignore exclusion)

**Commit:** 1b8c915

**Проблема:**
- `.gitignore` rule `KNOWLEDGE_BASE/*_ALL.json` исключал нужные файлы
- Миграция находила только 152 entities вместо 449

**Исправление:**
```diff
# .gitignore
- KNOWLEDGE_BASE/*_ALL.json
+ KNOWLEDGE_BASE/parsed_chats.json
```

**Добавлены файлы:**
- `KNOWLEDGE_BASE/curator_corrections_ALL.json` (275 entries)
- `KNOWLEDGE_BASE/student_questions_ALL.json` (500+ questions)

---

### Error 4: AttributeError - CuratorCorrection.original_text

**Commit:** 11a0eb9

**Проблема:**
```python
# ❌ ОШИБКА
"title": correction.original_text[:100]  # AttributeError: no attribute 'original_text'
```

**Исправление:**
```python
# ✅ ИСПРАВЛЕНО
"title": correction.student_text[:100] if correction.student_text else correction.error_type
```

**Файл:** `scripts/migrate_to_qdrant.py:228`

---

### Error 5: Wrong Metadata Attributes

**Commit:** 11a0eb9

**Проблема:**
```python
# ❌ ОШИБКА - Эти атрибуты не существуют в модели CuratorCorrection
"metadata": {
    "correction_type": correction.correction_type.value,  # ❌
    "severity": correction.severity,                       # ❌
    "tags": correction.tags                                # ❌
}
```

**Исправление:**
```python
# ✅ ИСПРАВЛЕНО - Реальные атрибуты из модели
"metadata": {
    "error_type": correction.error_type,
    "related_technique": correction.related_technique,
    "related_lesson": correction.related_lesson,
    "curator_name": correction.curator_name,
    "student_name": correction.student_name,
    "has_explanation": bool(correction.explanation)
}
```

**Файл:** `scripts/migrate_to_qdrant.py:231-237`

**Урок:** Всегда проверяйте реальные атрибуты модели через:
```python
from bot.models.knowledge_entities import CuratorCorrection
print(CuratorCorrection.__annotations__)
```

---

### Error 6: Point ID Format (КРИТИЧЕСКАЯ ОШИБКА!)

**Commit:** 480a2ee

**Проблема:**
```python
# ❌ ОШИБКА - String IDs отклоняются Qdrant
entity = {
    "id": f"faq_{entity_id}",              # "faq_0" - REJECTED
    "id": f"lesson_{lesson_number}",       # "lesson_5" - REJECTED
    "id": f"question_{entity_id}"          # "question_600" - REJECTED
}
```

**Ошибка Qdrant:**
```
Format error in JSON body: value question_600 is not a valid point ID,
valid values are either an unsigned integer or a UUID
```

**Исправление:**
```python
# ✅ ИСПРАВЛЕНО - Integer IDs
entity = {
    "id": entity_id,  # 0, 1, 2, 3, ... - ACCEPTED
}
```

**Затронутые строки:**
- FAQ: `migrate_to_qdrant.py:180`
- Lessons: `migrate_to_qdrant.py:202`
- Corrections: `migrate_to_qdrant.py:226`
- Questions: `migrate_to_qdrant.py:251`
- Brainwrites: `migrate_to_qdrant.py:273`

**Результат:**
- До исправления: **0/980 entities загружены** (все отклонены)
- После исправления: **980/980 entities загружены** (100% success)

**Урок:** Qdrant API очень строго относится к типам данных. Всегда используйте integer или UUID для Point IDs.

---

## Структура Entity

### Entity Types

| Type | Описание | Количество | Файл источника |
|------|----------|------------|----------------|
| `faq` | Часто задаваемые вопросы | 25 | `FAQ_EXTENDED.md` |
| `lesson` | Уроки курса (chunks) | 127 | `KNOWLEDGE_BASE_FULL.md` |
| `correction` | Корректировки куратора | 275 | `curator_corrections_ALL.json` |
| `question` | Вопросы студентов | 500 | `student_questions_ALL.json` |
| `brainwrite` | Примеры работ | 53 | `student_brainwrites_SAMPLE.json` |
| **ВСЕГО** | | **980** | |

---

### Entity Schema

```python
{
    "id": int,                    # Sequential: 0, 1, 2, ...
    "entity_type": str,           # "faq" | "lesson" | "correction" | "question" | "brainwrite"
    "title": str,                 # Краткий заголовок (до 100 символов)
    "content": str,               # Полный текст для semantic search
    "metadata": {
        # Зависит от entity_type
        # FAQ: category, keywords, frequency
        # Lesson: lesson_number, category, chunk_index, total_chunks, key_concepts
        # Correction: error_type, related_technique, related_lesson, curator_name, student_name
        # Question: category, lesson_reference, student_name
        # Brainwrite: student_name, lesson_number, technique_used, quality_rating
    }
}
```

---

### Пример: FAQ Entity

```json
{
    "id": 0,
    "entity_type": "faq",
    "title": "Вес встал, не уходит. Что делать?",
    "content": "FAQ (ЧАСТЫЙ ВОПРОС)\n\nQ: Вес встал, не уходит...\n\nA: Остановка веса...",
    "metadata": {
        "category": "ПИТАНИЕ И ПИЩЕВОЕ ПОВЕДЕНИЕ (61 вопрос)",
        "keywords": ["мозгоритм", "встал", "вторичные", "выгоды", ...],
        "frequency": null
    }
}
```

---

### Пример: Lesson Entity

```json
{
    "id": 25,
    "entity_type": "lesson",
    "title": "Урок 1: Введение в курс \"Всепрощающая\"",
    "content": "УРОК 1: Введение...\n\nВ этом уроке вы узнаете...",
    "metadata": {
        "lesson_number": 1,
        "category": "introduction",
        "chunk_index": 0,
        "total_chunks": 2,
        "key_concepts": ["мозгоритмы", "прощение", "курс"]
    }
}
```

---

### Пример: Correction Entity

```json
{
    "id": 152,
    "entity_type": "correction",
    "title": "Студентка написала мозгоритм на похудение, но формулировка неточная",
    "content": "КОРРЕКТИРОВКА КУРАТОРА\n\nОшибка студента: ...\n\nКорректировка: ...",
    "metadata": {
        "error_type": "Неточная формулировка",
        "related_technique": "Мозгоритмы",
        "related_lesson": "Урок 5",
        "curator_name": "Анна Игнатова",
        "student_name": "Мария К.",
        "has_explanation": true
    }
}
```

---

## Процесс миграции

### 1. Парсинг источников

```python
from parse_knowledge_base import KnowledgeBaseParser

parser = KnowledgeBaseParser(kb_dir)

# Parse FAQ
faq_entries = parser.parse_faq(kb_dir / "FAQ_EXTENDED.md")

# Parse Lessons
lessons = parser.parse_lessons(kb_dir / "KNOWLEDGE_BASE_FULL.md")

# Parse Corrections
corrections = parser.parse_corrections(kb_dir / "curator_corrections_ALL.json")

# Parse Questions
questions = parser.parse_questions(kb_dir / "student_questions_ALL.json", sample_limit=500)

# Parse Brainwrites
brainwrites = parser.parse_brainwrites(kb_dir / "student_brainwrites_SAMPLE.json", sample_limit=200)
```

---

### 2. Генерация Embeddings

```python
from sentence_transformers import SentenceTransformer

encoder = SentenceTransformer('all-MiniLM-L6-v2')

# Для каждого entity
for entity in all_entities:
    # Генерируем embedding из content
    vector = encoder.encode(entity["content"]).tolist()

    # vector = [float, float, ...] (384 dimensions)
```

**Важно:**
- Модель загружается **один раз** при инициализации
- Embeddings генерируются **локально** (без OpenAI API)
- Стоимость: **$0** (бесплатно)

---

### 3. Создание Points

```python
from qdrant_client.models import PointStruct

points = []

for entity in entities:
    # Генерировать embedding
    vector = encoder.encode(entity["content"]).tolist()

    # Создать payload
    payload = {
        "entity_type": entity["entity_type"],
        "title": entity["title"],
        "content": entity["content"],
        "metadata": entity["metadata"],
        "created_at": datetime.utcnow().isoformat()
    }

    # Создать point
    point = PointStruct(
        id=entity["id"],      # Integer!
        vector=vector,        # 384 floats
        payload=payload
    )

    points.append(point)
```

---

### 4. Batch Upload

```python
from qdrant_client import QdrantClient

client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

# Upload batch (50 points per batch)
batch_size = 50

for i in range(0, len(points), batch_size):
    batch = points[i:i + batch_size]

    client.upsert(
        collection_name="course_knowledge",
        points=batch
    )

    print(f"Uploaded {i + len(batch)}/{len(points)}")
```

**Рекомендации:**
- Batch size: 50 (оптимально для скорости и надёжности)
- Timeout: 60 секунд на batch
- Retry logic: exponential backoff при ошибках

---

### 5. Checkpoint System

```python
# Сохранить checkpoint после каждого batch
checkpoint = {
    "uploaded_ids": list(uploaded_ids),
    "uploaded_entities": stats["uploaded_entities"],
    "timestamp": datetime.utcnow().isoformat()
}

with open(checkpoint_file, 'w') as f:
    json.dump(checkpoint, f, indent=2)
```

**Преимущества:**
- Resumable loading (при обрыве можно продолжить)
- Защита от дубликатов (проверка `id in uploaded_ids`)
- Tracking прогресса

---

## Примеры кода

### Создание Collection

```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from sentence_transformers import SentenceTransformer

client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
encoder = SentenceTransformer('all-MiniLM-L6-v2')

# Определить размер вектора
test_vector = encoder.encode("test").tolist()
vector_size = len(test_vector)  # 384

# Создать collection
client.create_collection(
    collection_name="course_knowledge",
    vectors_config=VectorParams(
        size=vector_size,
        distance=Distance.COSINE
    )
)
```

---

### Semantic Search

```python
# Query
query = "как простить обиду"

# Генерировать query vector
query_vector = encoder.encode(query).tolist()

# Search
search_result = client.search(
    collection_name="course_knowledge",
    query_vector=query_vector,
    limit=5,
    score_threshold=0.6
)

# Results
for hit in search_result:
    print(f"Score: {hit.score:.4f}")
    print(f"Title: {hit.payload['title']}")
    print(f"Type: {hit.payload['entity_type']}")
    print()
```

---

### Hybrid Search (Vector + Filters)

```python
from qdrant_client.models import Filter, FieldCondition, MatchValue

# Search с фильтром по entity_type
search_result = client.search(
    collection_name="course_knowledge",
    query_vector=query_vector,
    query_filter=Filter(
        must=[
            FieldCondition(
                key="entity_type",
                match=MatchValue(value="faq")
            )
        ]
    ),
    limit=5
)
```

---

### Проверка статистики

```python
# Get collection info
collection_info = client.get_collection("course_knowledge")

print(f"Points count: {collection_info.points_count}")
print(f"Vector size: {collection_info.config.params.vectors.size}")
print(f"Distance: {collection_info.config.params.vectors.distance}")
print(f"Status: {collection_info.status}")
```

---

## Troubleshooting

### Проблема 1: "Format error in JSON body: value X is not a valid point ID"

**Причина:** Используются string IDs вместо integer

**Решение:**
```python
# ❌ НЕ ТАК
entity["id"] = f"faq_{idx}"

# ✅ ТАК
entity["id"] = idx  # Integer
```

---

### Проблема 2: "Vector dimension mismatch"

**Причина:** Размер вектора не соответствует collection config

**Решение:**
```python
# Проверить размер вектора
vector = encoder.encode(text).tolist()
print(f"Vector size: {len(vector)}")  # Должно быть 384

# Проверить collection config
collection_info = client.get_collection("course_knowledge")
print(f"Expected size: {collection_info.config.params.vectors.size}")
```

---

### Проблема 3: AttributeError при парсинге

**Причина:** Использованы несуществующие атрибуты модели

**Решение:**
```python
# Проверить доступные атрибуты
from bot.models.knowledge_entities import FAQEntry
print(FAQEntry.__annotations__)

# Использовать только реальные атрибуты
# ✅ faq.frequency
# ❌ faq.importance
```

---

### Проблема 4: Миграция застревает на N entities

**Причина:** Railway deployment перезапустился, процесс прервался

**Решение:**
```bash
# Перезапустить миграцию с checkpoint (reset=false)
curl -X POST "https://ignatova-stroinost-bot-production.up.railway.app/api/admin/qdrant/migrate" \
  -H "Content-Type: application/json" \
  -d '{"batch_size": 50, "reset": false}'
```

Checkpoint автоматически пропустит уже загруженные entities.

---

### Проблема 5: "Application failed to respond (502)"

**Причина:** Приложение перегружено долгой миграцией

**Решение:**
- Проверить прогресс **напрямую через Qdrant API**:
```bash
curl -s "https://33d94c1b-cc7f-4b71-82cc-dcee289122f0.eu-central-1-0.aws.cloud.qdrant.io:6333/collections/course_knowledge" \
  -H "api-key: YOUR_API_KEY" | python3 -m json.tool
```

- Миграция **продолжается в фоне** даже если Railway API не отвечает
- Подождать завершения deployment и проверить статус

---

## Полезные скрипты

### Локальный тест миграции

```bash
python3 test_qdrant_local.py
```

Проверяет:
- Подключение к Qdrant Cloud
- Semantic search
- Upload test entity

---

### Мониторинг прогресса

```bash
bash check_qdrant_progress.sh
```

Показывает прогресс миграции в real-time через Qdrant API.

---

### Проверка через curl

```bash
# Статус collection
curl -s "https://QDRANT_URL/collections/course_knowledge" \
  -H "api-key: API_KEY" | jq '.result.points_count'

# Пример точек
curl -s -X POST "https://QDRANT_URL/collections/course_knowledge/points/scroll" \
  -H "api-key: API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"limit": 3, "with_payload": true, "with_vector": false}' | jq
```

---

## Резюме требований

### Обязательные требования

1. **Point ID:** Integer или UUID (НЕ string!)
2. **Vector:** List of 384 floats (from all-MiniLM-L6-v2)
3. **Payload:** Обязательные поля - entity_type, title, content
4. **Batch size:** Рекомендуется 50 entities
5. **Timeout:** Минимум 60 секунд на batch

### Частые ошибки

1. ❌ String IDs → ✅ Integer IDs
2. ❌ Несуществующие атрибуты → ✅ Проверка через `__annotations__`
3. ❌ Неправильный метод парсера → ✅ Проверка имени метода
4. ❌ Файлы в .gitignore → ✅ Добавить в Git

### Рекомендации

- Всегда тестируйте локально через `test_qdrant_local.py`
- Используйте checkpoint system для resumable loading
- Мониторьте прогресс через Qdrant API напрямую
- При ошибках - читайте документацию Qdrant: https://qdrant.tech/documentation/

---

## Документация и ссылки

- **Qdrant API Reference:** https://api.qdrant.tech/api-reference
- **Qdrant Cloud Dashboard:** https://cloud.qdrant.io
- **Sentence Transformers:** https://www.sbert.net/docs/pretrained_models.html
- **Railway Project:** https://railway.app/project/a470438c-3a6c-4952-80df-9e2c067233c6

---

**Последнее обновление:** 14 ноября 2025

**Авторы исправлений:**
- Error 1-5: commits ed90ee8, 9da27f9, 1b8c915, 11a0eb9
- Error 6 (критическая): commit 480a2ee
