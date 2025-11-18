# Graphiti Knowledge Graph Integration

> Дата создания: 13 ноября 2025
> Статус: Активная (Neo4j Aura)

## Обзор

Graphiti - система temporal knowledge graph для гибридного поиска по базе знаний. Использует Neo4j для хранения entities и relationships.

### Почему Graphiti

- Deprecated Zep Cloud search API (больше не поддерживается)
- Нужен semantic + full-text + graph traversal search
- Temporal knowledge graph с bi-temporal моделью
- Собственный контроль над данными (Neo4j Aura)

### Преимущества новой архитектуры

| Функция | Zep Cloud (старое) | Graphiti (новое) |
|---------|-------------------|------------------|
| Semantic search | ❌ Deprecated | ✅ Vector embeddings |
| Full-text search | ❌ Нет | ✅ BM25 keyword matching |
| Graph relationships | ❌ Нет | ✅ Traversal по связям |
| Контроль данных | ❌ Cloud-only | ✅ Свой Neo4j |
| Стоимость | 💰 Platform fee | ✅ Neo4j Free tier |
| Temporal model | ❌ Нет | ✅ Bi-temporal |
| Hybrid search | ❌ Нет | ✅ Все методы |

---

## Архитектура (Variant C - Full Graphiti)

### ЭТАП 1: Инфраструктура

**Основные компоненты:**

1. **`bot/services/graphiti_service.py`** - клиент для Graphiti (350+ строк)
   - `health_check()`, `get_graph_stats()`
   - `add_episode()` - добавление знаний
   - `search_semantic()` - векторный поиск
   - `search_hybrid()` - комбинированный поиск

2. **`bot/config.py`** - Neo4j credentials
   - `NEO4J_URI`
   - `NEO4J_USER`
   - `NEO4J_PASSWORD`

3. **Тестирование и документация:**
   - `scripts/test_neo4j_connection.py` - тестирование подключения
   - `docs/NEO4J_SETUP.md` - полный гайд по настройке

4. **Зависимости (`requirements.txt`):**
   - `graphiti-core==0.18.9` (см. раздел "Версии и совместимость")
   - `neo4j>=5.0.0`

---

### ЭТАП 2: Data Modeling

**Файл:** `bot/models/knowledge_entities.py` (450+ строк)

**6 Pydantic схем:**

1. `CourseLesson` - уроки курса (с chunking)
2. `FAQEntry` - часто задаваемые вопросы
3. `CuratorCorrection` - корректировки куратора
4. `BrainwriteTechnique` - техники brainwrite
5. `StudentQuestion` - вопросы студентов
6. `BrainwriteExample` - примеры работ

**Парсер:** `scripts/parse_knowledge_base.py` (550+ строк)
- FAQ_EXTENDED.md → 25 FAQ entries
- KNOWLEDGE_BASE_FULL.md → 149 lesson chunks (60 уроков, 800 слов/chunk)
- curator_corrections_ALL.json → 275 corrections

**Итого:** 449 entities готовы к загрузке

---

### ЭТАП 3: Loading System

**1. Batch loader:** `scripts/load_knowledge_to_graphiti.py` (320+ строк)

Возможности:
- Tiered loading: Tier 1 (FAQ), Tier 2 (Lessons+Corrections)
- Checkpoint system для resumable loading
- Exponential backoff retry logic

**CLI использование:**
```bash
python load_knowledge_to_graphiti.py --tier 1 --batch-size 50
```

**2. Admin API:** `bot/api/admin_endpoints.py` (335+ строк)

Endpoints:
- `POST /api/admin/load_knowledge` - запуск загрузки
- `GET /api/admin/load_status` - прогресс загрузки
- `GET /api/admin/stats` - статистика Neo4j
- `POST /api/admin/clear_knowledge` - очистка графа
- `POST /api/admin/debug_indices` - диагностика индексов (см. раздел "Диагностика")

Фоновая загрузка с real-time monitoring.

**3. Мониторинг:** `scripts/monitor_knowledge_loading.sh`

---

### ЭТАП 4: Integration

**1. Гибридный поиск:** `bot/services/knowledge_search.py` (400+ строк)

- `SearchStrategy` enum: SEMANTIC, FULLTEXT, GRAPH, HYBRID, FALLBACK
- `SearchResult` модель с relevance scoring
- `route_query()` - автоматический выбор стратегии
- `format_context_for_llm()` - форматирование для AI
- Fallback к локальным MD файлам

**2. Интеграция в бота:** `bot/agent.py`

**Многоуровневый fallback:**
```
1. Graphiti hybrid search (primary) - Neo4j knowledge graph
2. Zep Cloud search (legacy) - keyword matching
3. Local files (встроено в Graphiti) - MD файлы
```

---

## Критические исправления

### ✅ ИСПРАВЛЕНИЕ #1: graphiti-core reasoning.effort Ошибка

**Дата:** 14 ноября, день

**Проблема:**
```
openai.BadRequestError: Unsupported parameter: 'reasoning.effort' is not supported with this model (gpt-4o-mini)
```

**Root Cause:**
- В `requirements.txt` указана версия `graphiti-core==0.3.18` - **НЕСУЩЕСТВУЕТ** в PyPI
- Версии 0.19.0+ используют параметр `reasoning.effort` для reasoning models (GPT-5, o1, o3)
- GPT-4o-mini **НЕ ПОДДЕРЖИВАЕТ** reasoning.effort (это обычная chat model, не reasoning model)

**Решение (commit 32ead70):**

```diff
# requirements.txt
- graphiti-core==0.3.18  # Несуществующая версия
+ graphiti-core==0.18.9  # Последняя стабильная БЕЗ reasoning.effort
```

**Почему именно 0.18.9:**
- ✅ Версия существует в PyPI
- ✅ НЕ использует параметр `reasoning.effort`
- ✅ Работает с GPT-4o-mini без ошибок
- ✅ Сохраняет все фичи knowledge graph
- ✅ Стабильная (октябрь 2024)

**Результат:**
```
✅ HTTP/1.1 200 OK - все OpenAI запросы успешны
✅ Episodes добавляются в Neo4j
✅ 99 nodes + 179 relationships созданы за 5 минут
✅ НЕТ ошибок reasoning.effort
```

**Дополнительно:** Строгое ограничение на базу знаний (RAG pattern)

**Проблема:** Бот мог использовать общие знания GPT вместо базы знаний курса.

**Решения:**

**1. `data/instruction.json` - добавлено критическое ограничение:**
```json
{
  "system_instruction": "# ⚠️ КРИТИЧЕСКОЕ ОГРАНИЧЕНИЕ - ПРИОРИТЕТ #1\n\n**ТЫ ДОЛЖЕН ОТВЕЧАТЬ ТОЛЬКО НА ОСНОВЕ БАЗЫ ЗНАНИЙ КУРСА**\n\n❌ ЗАПРЕЩЕНО использовать:\n- Общие знания GPT о психологии/саморазвитии\n- Информацию из training data\n- Собственные предположения\n\n✅ ИСПОЛЬЗУЙ ТОЛЬКО:\n- Информацию из секции '=== РЕЛЕВАНТНАЯ ИНФОРМАЦИЯ ИЗ БАЗЫ ЗНАНИЙ ==='\n- Методологию курса 'Всепрощающая'\n- Техники мозгоритмов\n\n⚠️ ЕСЛИ информации НЕТ в базе знаний:\nОтветь: \"[Имя], по этому вопросу рекомендую обратиться к Наталье напрямую 🌸\"\n\n**НЕ придумывай информацию! НЕ додумывай советы! ТОЛЬКО база знаний курса!**\n..."
}
```

**2. `bot/agent.py` - RAG pattern в коде:**
```python
# Добавляем контекст из базы знаний с СТРОГИМ RAG pattern
if knowledge_context:
    system_prompt += f"""

⚠️ ОБЯЗАТЕЛЬНОЕ ПРАВИЛО ГЕНЕРАЦИИ ОТВЕТА:
Ты ДОЛЖЕН использовать ТОЛЬКО информацию из раздела БАЗА ЗНАНИЙ ниже.
ЗАПРЕЩЕНО использовать свои общие знания GPT о психологии или других темах.
Если ответа НЕТ в БАЗЕ ЗНАНИЙ - скажи что нужно обратиться к Наталье.
НЕ придумывай информацию которой нет в БАЗЕ ЗНАНИЙ!

=== БАЗА ЗНАНИЙ КУРСА "ВСЕПРОЩАЮЩАЯ" ===
{knowledge_context}
=== КОНЕЦ БАЗЫ ЗНАНИЙ ===

ВАЖНО: Формулируй ответ используя ТОЛЬКО информацию из БАЗЫ ЗНАНИЙ выше!
"""
else:
    logger.info("📭 Контекст из базы знаний пуст")
    # Если базы знаний нет - возвращаем fallback сообщение
    user_name_display = user_name if user_name else "Дорогая"
    return f"{user_name_display}, по этому вопросу рекомендую обратиться к Наталье напрямую 🌸"
```

**Версия обновлена:**
- **instruction.json version:** 1.2 Strict RAG
- **Last updated:** 2025-11-14

---

### ✅ ИСПРАВЛЕНИЕ #2: Graphiti Dependency Conflicts

**Дата:** 13 ноября, ночь

**Проблема:** Множественные dependency conflicts при обновлении graphiti-core до 0.23.1

**Root Cause:** graphiti-core 0.23.1 требует более новые версии зависимостей:
- `openai>=1.91.0` (было `1.54.5`)
- `pydantic>=2.11.5` (было `2.8.2`)
- `python-dotenv>=1.0.1` (было `1.0.0`)
- `tenacity>=9.0.0` (streamlit 1.28.1 требовал `tenacity<9`)

**Исправления:**
```diff
# requirements.txt
- openai==1.54.5
+ openai>=1.91.0

- pydantic==2.8.2
+ pydantic>=2.11.5

- python-dotenv==1.0.0
+ python-dotenv>=1.0.1

- streamlit==1.28.1
+ streamlit>=1.51.0

graphiti-core==0.23.1  # Updated from >=0.3.0 to fix OpenAI Unicode errors
```

**Порядок исправления (6 deployments):**
1. ❌ Deployment #1 Failed: `openai==1.54.5` incompatible → Commit: d077c80
2. ❌ Deployment #2 Failed: `pydantic==2.8.2` incompatible → Commit: 46c7c52
3. ❌ Deployment #3 Failed: `python-dotenv==1.0.0` incompatible → Commit: 346593b
4. ❌ Deployment #4 Failed: Railway deployed stale code → Commit: 38b4bbd (force rebuild)
5. ❌ Deployment #5 Failed: `streamlit/tenacity` conflict → Commit: 95a8507
6. ✅ Deployment #6 Success: All dependencies compatible

**Урок:** При обновлении major версий фреймворков (graphiti-core 0.12.4 → 0.23.1), всегда проверяйте requirements их зависимостей. Dependency conflicts могут быть CASCADE - один конфликт ведёт к другому.

---

### ✅ ИСПРАВЛЕНИЕ #3: Graphiti Loading + GPT-4o-mini

**Дата:** 14 ноября, утро

**Проблемы обнаружены:**

**1. OpenAI Rate Limit Exceeded:**
- Graphiti использовал **GPT-4o по умолчанию** (очень дорого + жёсткие rate limits)
- Загрузка застревала: `Rate limit exceeded. Please try again later.`
- 0 episodes сохранялись в Neo4j
- Стоимость загрузки: $35-50 для 1,002 entities

**2. Checkpoint Bug:**
- Параметр `reset_checkpoint` в API не работал
- Checkpoint файл не удалялся при `reset_checkpoint=True`
- Загрузка пропускала entities из старого checkpoint (skipped)
- Progress застревал на 25/1002

**Решения:**

**1. Переключение на GPT-4o-mini (commit 29a3d43)**

**Файлы:**
- `bot/config.py` - добавлены `MODEL_NAME` и `SMALL_MODEL_NAME`
- `bot/services/graphiti_service.py` - устанавливает env vars перед инициализацией

**Код:**
```python
# bot/config.py:19-23
MODEL_NAME = os.getenv('MODEL_NAME', 'gpt-4o-mini')
SMALL_MODEL_NAME = os.getenv('SMALL_MODEL_NAME', 'gpt-4o-mini')

# bot/services/graphiti_service.py:82-83
os.environ['MODEL_NAME'] = MODEL_NAME
os.environ['SMALL_MODEL_NAME'] = SMALL_MODEL_NAME
```

**Результат:**
- ✅ Снижение стоимости: $35-50 → $2-3 (15-17x экономия!)
- ✅ Нет rate limit ошибок
- ✅ Достаточное качество для entity extraction

**2. Исправление Checkpoint Bug (commit a388a6f)**

**Файл:** `bot/api/admin_endpoints.py:238-241`

**Код:**
```python
# КРИТИЧЕСКИ ВАЖНО: Удалить checkpoint если reset_checkpoint=True
if reset_checkpoint and checkpoint_file.exists():
    checkpoint_file.unlink()
    logger.info(f"🗑️ Checkpoint удалён: {checkpoint_file}")
```

**Результат:**
- ✅ Checkpoint удаляется при `reset_checkpoint=True`
- ✅ Загрузка начинается с entity #1
- ✅ Progress счётчик работает корректно

---

### ✅ ИСПРАВЛЕНИЕ #4: Neo4j Indices Initialization

**Дата:** 13 ноября, вечер

**Проблема:** Episodes не сохранялись в Neo4j

После реализации Graphiti и попытки загрузки 1002 entities обнаружилась критическая проблема:
- `add_episode()` выполнялся без ошибок
- Загрузка показывала "completed" (346/346 entities)
- Но Neo4j граф оставался **пустым** (0 nodes, 0 episodes)

**Причина:**
Graphiti требует **обязательный вызов** `build_indices_and_constraints()` перед началом работы. Этот метод создает необходимые индексы и constraints в Neo4j для корректного сохранения episodes.

**Решение (коммит 336482c):**
Добавлен вызов `build_indices_and_constraints()` при инициализации `GraphitiService`:

```python
# bot/services/graphiti_service.py:84-92
# КРИТИЧЕСКИ ВАЖНО: Создать индексы и constraints в Neo4j
# Без этого episodes не сохраняются!
logger.info("Building Neo4j indices and constraints...")
import asyncio
loop = asyncio.new_event_loop()
loop.run_until_complete(self.graphiti_client.build_indices_and_constraints())
loop.close()
logger.info("✅ Neo4j indices and constraints created")
```

**Урок:**
При работе с graphiti-core >= 0.3.0:
1. **ВСЕГДА** вызывай `build_indices_and_constraints()` при первой инициализации
2. Этот метод нужно вызвать **один раз** (он идемпотентен)
3. Без этого episodes не сохраняются в Neo4j, но ошибок не возникает (silent failure)

**Документация:** https://github.com/getzep/graphiti#usage

---

## Диагностика

### DEBUG: Диагностический инструментарий для Neo4j

**Дата:** 13 ноября, поздний вечер

**Проблема:** После исправления lazy initialization (коммит e4bac7d) Graphiti service инициализируется успешно, но Neo4j граф остаётся **пустым** несмотря на "успешную" загрузку 346 entities.

**Симптомы:**
- `/api/admin/load_knowledge` завершается с `"progress": 346/346` (100%)
- Нет ошибок в логах
- `/api/admin/stats` показывает `0 nodes, 0 relationships, 0 episodes`
- **Silent failure** - самый опасный тип ошибки

**Решение (коммит 0dd0d81): Диагностический инструментарий**

#### 1. Улучшенное логирование в `_ensure_indices()`:

```python
# bot/services/graphiti_service.py:98-123
async def _ensure_indices(self):
    logger.info(f"🔍 _ensure_indices() called. Current state: _indices_built={self._indices_built}")

    if self._indices_built:
        logger.info("✅ Indices already built, skipping")
        return True

    try:
        logger.info("🔨 Building Neo4j indices and constraints...")
        logger.info(f"   Neo4j URI: {NEO4J_URI}")
        logger.info(f"   Calling graphiti_client.build_indices_and_constraints()...")

        await self.graphiti_client.build_indices_and_constraints()

        self._indices_built = True
        logger.info("✅ Neo4j indices and constraints created successfully")
        logger.info(f"   _indices_built flag set to: {self._indices_built}")

        # Проверяем что индексы действительно созданы
        indices_check = await self._verify_indices()
        logger.info(f"   Indices verification: {indices_check}")

        return True
    except Exception as e:
        logger.error(f"❌ Failed to build indices: {type(e).__name__}: {e}")
        logger.exception("Full traceback:")
        return False
```

#### 2. Метод `_verify_indices()` для проверки индексов:

```python
# bot/services/graphiti_service.py:125-154
async def _verify_indices(self) -> Dict[str, Any]:
    """Проверить что индексы и constraints действительно созданы в Neo4j"""
    try:
        with self.neo4j_driver.session() as session:
            # Получаем список индексов
            indices_result = session.run("SHOW INDEXES")
            indices = [record.data() for record in indices_result]

            # Получаем список constraints
            constraints_result = session.run("SHOW CONSTRAINTS")
            constraints = [record.data() for record in constraints_result]

            return {
                "indices_count": len(indices),
                "constraints_count": len(constraints),
                "indices": indices[:5],  # Первые 5 для логов
                "constraints": constraints[:5]
            }
    except Exception as e:
        logger.error(f"Failed to verify indices: {e}")
        return {"error": str(e), "indices_count": 0, "constraints_count": 0}
```

#### 3. Debug endpoint `POST /api/admin/debug_indices`

**Использование:**
```bash
curl -X POST "https://ignatova-stroinost-bot-production.up.railway.app/api/admin/debug_indices"
```

**Что делает:**
1. **Шаг 1:** Проверяет начальное состояние Neo4j + флаг `_indices_built`
2. **Шаг 2:** Вручную вызывает `_ensure_indices()`
3. **Шаг 3:** Проверяет созданные индексы в Neo4j (SHOW INDEXES, SHOW CONSTRAINTS)
4. **Шаг 4:** Добавляет тестовый episode
5. **Шаг 5:** Проверяет статистику Neo4j после episode
6. **Шаг 6:** Сравнивает до/после (nodes_added, episodes_added)

**Возможные диагнозы:**
- ❌ `_ensure_indices()` returned False
- ❌ No indices created in Neo4j
- ❌ Episode add failed
- ❌ **CRITICAL: Episode added successfully but NOT PERSISTED** (silent failure)
- ✅ SUCCESS: Indices created and episode persisted correctly

---

## Cost Optimization

### Graphiti Model Configuration

**Дата:** 13 ноября, ночь

**Проблема:** Graphiti по умолчанию использует GPT-4o, что очень дорого для обработки knowledge base.

**Стоимость загрузки 1002 entities:**
- С GPT-4o: $35-50 (3-5 API вызовов на entity)
- С GPT-4o-mini: $2-3 (15-17x дешевле!)

**Pricing:**
```
GPT-4o:       $2.50/1M input,  $10.00/1M output
GPT-4o-mini:  $0.15/1M input,  $0.60/1M output
Экономия:     17x               17x
```

**Решение:** Переключить Graphiti на GPT-4o-mini через environment variables

**Шаги конфигурации:**
1. Открой Railway Dashboard: https://railway.app/project/a470438c-3a6c-4952-80df-9e2c067233c6
2. Выбери сервис `ignatova-stroinost-bot`
3. Перейди в раздел **Variables**
4. Добавь две переменные:
   ```
   MODEL_NAME=gpt-4o-mini
   SMALL_MODEL_NAME=gpt-4o-mini
   ```
5. Сохрани - Railway автоматически перезапустит сервис

**Как работает:**
- Graphiti читает environment variables при инициализации
- `MODEL_NAME` - основная модель для entity/relationship extraction
- `SMALL_MODEL_NAME` - модель для вспомогательных операций (deduplication)
- Без этих переменных Graphiti использует GPT-4o по умолчанию

**Результат:**
- ✅ Текущие 449 entities продолжают работать
- ✅ Новые entities обрабатываются через GPT-4o-mini
- ✅ Стоимость загрузки оставшихся 553 entities: ~$2 вместо ~$20
- ✅ Качество: GPT-4o-mini достаточно для entity extraction

**⚠️ Важно:** `.env` не коммитится в Git (содержит API keys). Переменные настраиваются **только в Railway Dashboard**.

**Документация:** https://help.getzep.com/graphiti/configuration/llm-configuration

---

## Использование

### 1. Загрузка базы знаний (один раз)

```bash
# Через Admin API
curl -X POST "https://ignatova-stroinost-bot-production.up.railway.app/api/admin/load_knowledge" \
  -H "Content-Type: application/json" \
  -d '{"tier": null, "batch_size": 50}'

# Мониторинг прогресса
./scripts/monitor_knowledge_loading.sh
```

### 2. Проверка статистики

```bash
curl "https://ignatova-stroinost-bot-production.up.railway.app/api/admin/stats"
```

### 3. Работа бота

- Бот автоматически использует Graphiti для поиска
- При недоступности Graphiti → fallback к Zep
- При недоступности Zep → fallback к локальным файлам
- Логи показывают выбранную стратегию

---

## Railway Environment Variables

```bash
# Neo4j Aura (обязательно)
NEO4J_URI=neo4j+s://51b8e0bb.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=fLWG-zJubpul21UaKELz77ISQIPFLWk-oG06kY4JzzM
GRAPHITI_ENABLED=true

# Cost Optimization (рекомендуется)
MODEL_NAME=gpt-4o-mini
SMALL_MODEL_NAME=gpt-4o-mini
```

---

## Результаты

**Код:** +2,891 строк
**Файлы:** 10 новых + 4 измененных
**Entities:** 449 готовы к загрузке
**Neo4j:** Aura Free tier (1GB, ~100-200K nodes capacity)

**Commits:**
- 2669287, 92516c8, 67b93f0 - Полная реализация Graphiti
- 32ead70 - Откат graphiti-core на 0.18.9 + строгое ограничение на базу знаний
- d077c80, 46c7c52, 346593b, 38b4bbd, 95a8507 - Исправление dependency conflicts
- 29a3d43 - Переключение на GPT-4o-mini
- a388a6f - Исправление Checkpoint Bug
- 336482c - Neo4j Indices Initialization
- 0dd0d81 - Диагностический инструментарий

---

## Дополнительная документация

- `docs/NEO4J_SETUP.md` - настройка Neo4j Aura
- `docs/GRAPHITI_FINAL_SETUP.md` - финальная настройка
- `bot/services/knowledge_search.py` - примеры использования
- `scripts/parse_knowledge_base.py` - как добавить новые entities
