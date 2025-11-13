# Claude Code Configuration

## Язык общения
**ОБЯЗАТЕЛЬНОЕ ПРАВИЛО:** Всегда отвечай на русском языке во всех взаимодействиях с пользователем.

## Automatic GitHub Updates Rule

**ВАЖНОЕ ПРАВИЛО:** При любых изменениях в коде бота - СРАЗУ обновлять репозиторий на GitHub.

### Процедура обновления после изменений:

1. **После любого изменения в bot/**:
   ```bash
   git add .
   git commit -m "Описание изменений"
   git push origin main
   ```

2. **Типы изменений требующих немедленного обновления:**
   - Изменения в логике бота (`bot/agent.py`, `bot/handlers.py`)
   - Обновления конфигурации (`bot/config.py`, `.env`)
   - Новые функции или исправления багов
   - Изменения в деплойменте (`deploy/`)
   - Обновления зависимостей (`requirements.txt`)

3. **Формат коммит-сообщений:**
   - Краткое описание изменений
   - Подробности что именно исправлено/добавлено
   - Обязательная подпись Claude Code

### Почему это важно:

- Railway автоматически деплоит изменения с GitHub
- Синхронизация локального кода с продакшеном
- Возможность откатить изменения при проблемах
- Команда всегда видит актуальные изменения

### Команды для быстрого обновления:

```bash
# Проверить изменения
git status
git diff

# Зафиксировать все изменения
git add .
git commit -m "Bot updates: описание изменений

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>"

# Отправить на GitHub
git push origin main
```

**ВСЕГДА обновляй GitHub после изменений в коде!**

---

## Railway API Monitoring

**ВАЖНОЕ ПРАВИЛО:** При диагностике проблем с деплойментом на Railway - ВСЕГДА использовать Railway API для автоматической проверки логов и переменных окружения.

### Railway API Token

**Токен (обновлен 13 ноября 2025):** `74a44277-c21d-4210-b0aa-38a53d8bce94`
**Тип:** Project Token (полный доступ к проекту)
**Хранится в:** `.env` (переменная `RAILWAY_TOKEN`)
**API Endpoint:** `https://backboard.railway.app/graphql/v2`

**Старый токен (устарел):** `0bc5424e-585d-4761-a401-ff7443c6bd3a` - имел ограниченные права

### Обязательные проверки через API:

#### 1. Получить информацию о текущем пользователе:

```bash
curl -s "https://backboard.railway.app/graphql/v2" \
  -H "Authorization: Bearer 0bc5424e-585d-4761-a401-ff7443c6bd3a" \
  -H "Content-Type: application/json" \
  -X POST \
  -d '{"query":"query { me { id email name } }"}' | jq .
```

#### 2. Получить список проектов:

```bash
curl -s "https://backboard.railway.app/graphql/v2" \
  -H "Authorization: Bearer 0bc5424e-585d-4761-a401-ff7443c6bd3a" \
  -H "Content-Type: application/json" \
  -X POST \
  -d '{"query":"query { me { projects { edges { node { id name } } } } }"}' | jq .
```

#### 3. Получить переменные окружения проекта:

```bash
# Замените PROJECT_ID на реальный ID проекта
curl -s "https://backboard.railway.app/graphql/v2" \
  -H "Authorization: Bearer 0bc5424e-585d-4761-a401-ff7443c6bd3a" \
  -H "Content-Type: application/json" \
  -X POST \
  -d '{
    "query": "query { project(id: \"PROJECT_ID\") { services { edges { node { name variables { edges { node { name value } } } } } } } }"
  }' | jq .
```

#### 4. Получить логи деплоймента:

```bash
# Замените DEPLOYMENT_ID на реальный ID деплоймента
curl -s "https://backboard.railway.app/graphql/v2" \
  -H "Authorization: Bearer 0bc5424e-585d-4761-a401-ff7443c6bd3a" \
  -H "Content-Type: application/json" \
  -X POST \
  -d '{
    "query": "query { deployment(id: \"DEPLOYMENT_ID\") { buildLogs staticUrl status } }"
  }' | jq .
```

### Когда использовать Railway API:

✅ **ВСЕГДА проверяй через API:**
- Статус деплоймента после push на GitHub
- Переменные окружения (NEO4J_URI, GRAPHITI_ENABLED, etc.)
- Логи при ошибках инициализации сервисов
- Статус сервисов (active, failed, building)

❌ **НЕ спрашивай пользователя:**
- "Проверьте переменные на Railway" → проверь сам через API
- "Скопируйте логи Railway" → получи логи через API
- "Какой статус деплоймента?" → проверь через API

### Примеры использования:

**При ошибке "Graphiti service not available":**
1. Проверь переменные через API → найди NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD, GRAPHITI_ENABLED
2. Получи логи последнего деплоймента → найди строки с "Graphiti" или "Neo4j"
3. Проверь статус деплоймента → убедись что статус "ACTIVE"

**При изменениях в коде:**
1. После `git push` → подожди 2 минуты
2. Проверь статус деплоймента через API
3. Получи логи если статус "FAILED"

### Хранение токена:

Токен уже добавлен в `.env`:
```bash
RAILWAY_TOKEN=74a44277-c21d-4210-b0aa-38a53d8bce94
```

Использование из кода:
```python
import os
railway_token = os.getenv('RAILWAY_TOKEN')
```

### Инструменты мониторинга Railway:

**1. Bash скрипт: `scripts/railway_logs.sh`**

Простой bash скрипт для базовых операций:
```bash
# Показать последние 10 deployments
./scripts/railway_logs.sh list

# Показать логи последнего deployment
./scripts/railway_logs.sh logs

# Мониторинг логов в реальном времени
./scripts/railway_logs.sh monitor

# Показать переменные окружения
./scripts/railway_logs.sh env
```

**2. Python скрипт: `scripts/railway_monitor.py`**

Более функциональный Python скрипт:
```bash
# Показать последние 5 deployments
python3 scripts/railway_monitor.py list --limit 5

# Показать информацию о последнем deployment
python3 scripts/railway_monitor.py info

# Мониторинг в реальном времени
python3 scripts/railway_monitor.py monitor --interval 10
```

**Документация:** См. `RAILWAY_API.md` для полного описания API и инструментов

**Константы проекта:**
- Project ID: `a470438c-3a6c-4952-80df-9e2c067233c6`
- Service ID: `3eb7a84e-5693-457b-8fe1-2f4253713a0c`
- MySQL Service ID: `d203ed15-2d73-405a-8210-4c100fbaf133`

---

## ВАЖНАЯ ЗАМЕТКА: Graphiti Dependency Conflicts (13 ноября, ночь)

**Проблема:** Множественные dependency conflicts при обновлении graphiti-core до 0.23.1

**Root Cause:** graphiti-core 0.23.1 требует более новые версии зависимостей:
- `openai>=1.91.0` (было `1.54.5`)
- `pydantic>=2.11.5` (было `2.8.2`)

**Исправления:**
```diff
# requirements.txt
- openai==1.54.5
+ openai>=1.91.0

- pydantic==2.8.2
+ pydantic>=2.11.5

graphiti-core==0.23.1  # Updated from >=0.3.0 to fix OpenAI Unicode errors
```

**Порядок исправления:**
1. ❌ Deployment #1 Failed: `openai==1.54.5` incompatible with graphiti-core 0.23.1
   - Commit: d077c80 - Updated openai to >=1.91.0
2. ❌ Deployment #2 Failed: `pydantic==2.8.2` incompatible with graphiti-core 0.23.1
   - Commit: 46c7c52 - Updated pydantic to >=2.11.5
3. ✅ Deployment #3 Expected: All dependencies compatible

**Урок:** При обновлении major версий фреймворков (graphiti-core 0.12.4 → 0.23.1), всегда проверяйте requirements их зависимостей.

**Commits:**
- d077c80 - Fix: openai version conflict
- 46c7c52 - Fix: pydantic version conflict

---

## Последние обновления (13 ноября 2025)

### 🔧 КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Neo4j Indices Initialization (13 ноября, вечер)

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

### 🔍 DEBUG: Диагностический инструментарий для Neo4j (13 ноября, поздний вечер)

**Проблема:** После исправления lazy initialization (коммит e4bac7d) Graphiti service инициализируется успешно, но Neo4j граф остаётся **пустым** несмотря на "успешную" загрузку 346 entities.

**Симптомы:**
- `/api/admin/load_knowledge` завершается с `"progress": 346/346` (100%)
- Нет ошибок в логах
- `/api/admin/stats` показывает `0 nodes, 0 relationships, 0 episodes`
- **Silent failure** - самый опасный тип ошибки

**Гипотезы:**
1. `_ensure_indices()` не вызывается или возвращает False
2. `build_indices_and_constraints()` выполняется но не создаёт индексы
3. Episodes добавляются но не коммитятся в Neo4j
4. Проблема совместимости Graphiti/Neo4j Aura

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

#### 3. Debug endpoint `POST /api/admin/debug_indices`:

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

**Пример ответа:**

```json
{
  "success": true,
  "steps": {
    "1_initial_state": {
      "stats": {"total_nodes": 0, "total_episodes": 0},
      "indices_built_flag": false
    },
    "2_ensure_indices": {
      "result": true,
      "indices_built_flag_after": true
    },
    "3_verify_indices": {
      "indices_count": 5,
      "constraints_count": 3
    },
    "4_add_episode": {
      "success": true,
      "result": "episode_id_12345"
    },
    "5_stats_after": {
      "total_nodes": 15,
      "total_episodes": 1
    },
    "6_comparison": {
      "nodes_added": 15,
      "episodes_added": 1,
      "episode_persisted": true
    }
  },
  "diagnosis": "✅ SUCCESS: Indices created and episode persisted correctly"
}
```

**Файлы:**
- `bot/services/graphiti_service.py` (+30 строк логов + метод `_verify_indices`)
- `bot/api/admin_endpoints.py` (+~150 строк debug endpoint)

**Следующий шаг:** Запустить debug endpoint после деплоя → выявить корневую причину пустого графа

---

### 🧠 Graphiti Knowledge Graph - Полная реализация

**Добавлено:** Full Graphiti Architecture для гибридного поиска по базе знаний

**Почему Graphiti:**
- Deprecated Zep Cloud search API (больше не поддерживается)
- Нужен semantic + full-text + graph traversal search
- Temporal knowledge graph с bi-temporal моделью
- Собственный контроль над данными (Neo4j Aura)

#### ✅ Архитектура (Variant C - Full Graphiti):

**ЭТАП 1: Инфраструктура**
- `bot/services/graphiti_service.py` - клиент для Graphiti (350+ строк)
  - `health_check()`, `get_graph_stats()`
  - `add_episode()` - добавление знаний
  - `search_semantic()` - векторный поиск
  - `search_hybrid()` - комбинированный поиск
- `bot/config.py` - Neo4j credentials (NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
- `scripts/test_neo4j_connection.py` - тестирование подключения
- `docs/NEO4J_SETUP.md` - полный гайд по настройке
- `requirements.txt` - graphiti-core>=0.3.0, neo4j>=5.0.0

**ЭТАП 2: Data Modeling**
- `bot/models/knowledge_entities.py` - 6 Pydantic схем (450+ строк):
  - `CourseLesson` - уроки курса (с chunking)
  - `FAQEntry` - часто задаваемые вопросы
  - `CuratorCorrection` - корректировки куратора
  - `BrainwriteTechnique` - техники brainwrite
  - `StudentQuestion` - вопросы студентов
  - `BrainwriteExample` - примеры работ
- `scripts/parse_knowledge_base.py` - парсер MD/JSON → entities (550+ строк)
  - FAQ_EXTENDED.md → 25 FAQ entries
  - KNOWLEDGE_BASE_FULL.md → 149 lesson chunks (60 уроков, 800 слов/chunk)
  - curator_corrections_ALL.json → 275 corrections
  - **Итого:** 449 entities готовы к загрузке

**ЭТАП 3: Loading System**
- `scripts/load_knowledge_to_graphiti.py` - batch loader (320+ строк)
  - Tiered loading: Tier 1 (FAQ), Tier 2 (Lessons+Corrections)
  - Checkpoint system для resumable loading
  - Exponential backoff retry logic
  - CLI: `python load_knowledge_to_graphiti.py --tier 1 --batch-size 50`
- `bot/api/admin_endpoints.py` - удаленное управление (335+ строк)
  - `POST /api/admin/load_knowledge` - запуск загрузки
  - `GET /api/admin/load_status` - прогресс загрузки
  - `GET /api/admin/stats` - статистика Neo4j
  - `POST /api/admin/clear_knowledge` - очистка графа
  - Фоновая загрузка с real-time monitoring
- `scripts/monitor_knowledge_loading.sh` - мониторинг загрузки

**ЭТАП 4: Integration**
- `bot/services/knowledge_search.py` - гибридный поиск (400+ строк)
  - `SearchStrategy` enum: SEMANTIC, FULLTEXT, GRAPH, HYBRID, FALLBACK
  - `SearchResult` модель с relevance scoring
  - `route_query()` - автоматический выбор стратегии
  - `format_context_for_llm()` - форматирование для AI
  - Fallback к локальным MD файлам
- `bot/agent.py` - многоуровневый fallback:
  ```
  1. Graphiti hybrid search (primary) - Neo4j knowledge graph
  2. Zep Cloud search (legacy) - keyword matching
  3. Local files (встроено в Graphiti) - MD файлы
  ```

#### 📊 Результаты:
- **Код:** +2,891 строк
- **Файлы:** 10 новых + 4 измененных
- **Entities:** 449 готовы к загрузке
- **Neo4j:** Aura Free tier (1GB, ~100-200K nodes capacity)

#### 🚀 Использование:

**1. Загрузка базы знаний (один раз):**
```bash
# Через Admin API
curl -X POST "https://ignatova-stroinost-bot-production.up.railway.app/api/admin/load_knowledge" \
  -H "Content-Type: application/json" \
  -d '{"tier": null, "batch_size": 50}'

# Мониторинг прогресса
./scripts/monitor_knowledge_loading.sh
```

**2. Проверка статистики:**
```bash
curl "https://ignatova-stroinost-bot-production.up.railway.app/api/admin/stats"
```

**3. Работа бота:**
- Бот автоматически использует Graphiti для поиска
- При недоступности Graphiti → fallback к Zep
- При недоступности Zep → fallback к локальным файлам
- Логи показывают выбранную стратегию

#### ⚙️ Railway Environment Variables:

```bash
# Neo4j Aura (обязательно)
NEO4J_URI=neo4j+s://51b8e0bb.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=fLWG-zJubpul21UaKELz77ISQIPFLWk-oG06kY4JzzM
GRAPHITI_ENABLED=true
```

#### 🔧 Преимущества новой архитектуры:

| Функция | Zep Cloud (старое) | Graphiti (новое) |
|---------|-------------------|------------------|
| Semantic search | ❌ Deprecated | ✅ Vector embeddings |
| Full-text search | ❌ Нет | ✅ BM25 keyword matching |
| Graph relationships | ❌ Нет | ✅ Traversal по связям |
| Контроль данных | ❌ Cloud-only | ✅ Свой Neo4j |
| Стоимость | 💰 Platform fee | ✅ Neo4j Free tier |
| Temporal model | ❌ Нет | ✅ Bi-temporal |
| Hybrid search | ❌ Нет | ✅ Все методы |

#### 📚 Документация:
- `docs/NEO4J_SETUP.md` - настройка Neo4j Aura
- `bot/services/knowledge_search.py` - примеры использования
- `scripts/parse_knowledge_base.py` - как добавить новые entities

**Коммиты:** 2669287, 92516c8, 67b93f0

---

### 🗄️ MySQL интеграция для хранения переписок

**Добавлено:** Полная система хранения всех сообщений в MySQL базе данных

**Архитектура (адаптирована из GPTIFOBIZ):**

✅ **База данных:**
- `bot/database/database.py` - подключение к MySQL с connection pooling
- `bot/database/models.py` - SQLAlchemy модели:
  - `TelegramChat` - информация о чатах и пользователях
  - `TelegramMessage` - все сообщения с метаданными

✅ **Сервис хранения:**
- `bot/services/message_storage_service.py`
- Автоматическое сохранение всех типов сообщений
- Retry логика при database locks (exponential backoff)
- Обработка вложений и голосовых сообщений

✅ **API Endpoints:**
- `bot/api/message_endpoints.py` - REST API для доступа к данным:
  - `GET /api/chats` - список чатов с пагинацией
  - `GET /api/chats/{id}` - детали чата
  - `GET /api/chats/{id}/messages` - сообщения чата
  - `GET /api/search?q=...` - поиск по тексту сообщений
  - `GET /api/stats` - общая статистика
  - `GET /api/health/db` - проверка статуса БД

✅ **Интеграция:**
- `business_handler.py` - полное сохранение Business сообщений
- `main.py` - автоматическая инициализация БД при старте

**Что сохраняется:**
- ✅ Обычные текстовые сообщения + ответы бота
- ✅ Business API сообщения (с фильтрацией владельца)
- ✅ Голосовые сообщения с транскрипцией Whisper
- ✅ Метаданные вложений (фото, видео, документы)
- ✅ Информация о чатах и пользователях
- ✅ Модель AI использованная для ответа (gpt-4o/claude)

**Гибридный подход:**
- **Zep Cloud** - AI-память и семантический поиск (продолжает работать)
- **MySQL** - долговременное хранение для аналитики (новое)

**Документация:** `MYSQL_SETUP.md` - полный гайд по настройке

**Коммит:** d0adbd3

---

## Предыдущие исправления (13 ноября 2025)

### ✅ Исправлено дублирование источников

**Проблема:**
```
Бот: "Да, я здесь! 😊📚 **Источник:** EPISODES"
Бот: "📚 **Источник:** TECHNIQUES-сессия1"
```

**Причина:**
- GPT добавлял источники согласно инструкции в `data/instruction.json`
- Код в `bot/agent.py:454-457` программно добавлял источники повторно

**Решение:**
- Убрано программное добавление источников (bot/agent.py:447-457)
- GPT сам корректно указывает источники в ответах

**Файл:** `bot/agent.py` (коммит afc0789)

### ✅ Улучшена обработка ошибок голосовых сообщений

**Проблема:**
- Generic error: "🎤 Не удалось распознать голосовое сообщение"
- Пользователь не понимал причину ошибки

**Решение:**
Добавлены детальные error messages:

| Ошибка | Сообщение пользователю |
|--------|------------------------|
| `no_file_id` | "Не удалось получить голосовое сообщение от Telegram" |
| `too_long` | "Слишком длинное (320с). Максимум: 10 минут (600с)" |
| `too_short` | "Слишком короткое. Запишите хотя бы 1 секунду" |
| `timeout` | "Превышено время ожидания. Попробуйте ещё раз" |
| `api_error` | "Сервис распознавания временно недоступен" |

**Файлы:**
- `bot/handlers/message_handler.py:61-122` - `handle_voice_message()`
- `bot/handlers/message_handler.py:124-176` - `_process_voice_transcription()`

**Коммит:** afc0789

### 📋 Детальное логирование

Добавлено в `_process_voice_transcription()`:
```
🎤 Голосовое сообщение от Пользователь (ID: 123), длительность: 5с
📥 Получаем файл ABC123 от Telegram...
📥 URL файла получен: voice/file_123.oga
🎙️ Отправляем на транскрипцию (длительность: 5с)...
✅ Транскрипция успешна: 124 символов
```

### 🔐 Исключены большие файлы из Git

Добавлено в `.gitignore`:
```
# Large knowledge base files (>100MB)
KNOWLEDGE_BASE/parsed_chats.json
KNOWLEDGE_BASE/*_FULL.json
KNOWLEDGE_BASE/*_ALL.json
```

**Причина:** GitHub не принимает файлы > 100 MB

---

## Текущий статус бота

### ✅ Полностью рабочие компоненты:
- OpenAI GPT-4o (primary LLM)
- Anthropic Claude 3.5 Sonnet (fallback)
- Голосовые сообщения (Whisper API)
- Zep Cloud память и база знаний
- **MySQL база данных** - хранение всех переписок (новое!)
- REST API endpoints для доступа к истории сообщений
- Telegram Webhook
- Railway автодеплой

### 📊 Качество ответов:
- Источники указываются корректно (один раз)
- Детальные объяснения ошибок
- Полное логирование для диагностики

### 🔧 Railway переменные окружения:
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

# Database (новое!)
DATABASE_URL=mysql+pymysql://${MYSQL_USER}:${MYSQL_PASSWORD}@${MYSQL_HOST}:${MYSQL_PORT}/${MYSQL_DATABASE}
# Автоматически создается при добавлении MySQL плагина в Railway
```

### 📝 Важные документы:
- **SUCCESS_REPORT.md** - полный отчёт о запуске бота
- **FIX_GUIDE.md** - гайд по устранению проблем
- **DIAGNOSIS.md** - диагностика неполадок
- **MYSQL_SETUP.md** - настройка MySQL для хранения переписок (новое!)
- **CLAUDE.md** (этот файл) - конфигурация и история изменений

### 📊 Архитектура хранения данных:

**Гибридная система:**
- **Zep Cloud** (облако):
  - Семантическая память диалогов
  - Поиск по базе знаний
  - Контекст для AI генерации
  - Автоматическая очистка старых данных

- **MySQL** (Railway):
  - Долговременное хранение всех сообщений
  - Детальная аналитика и статистика
  - История переписок без ограничений
  - REST API для доступа к данным

**Преимущества:**
- Zep отвечает за "умную" память для AI
- MySQL отвечает за архив и аналитику
- Системы работают независимо - отказ одной не ломает другую
- Можно отключить MySQL (DATABASE_URL не настроен) - бот продолжит работать