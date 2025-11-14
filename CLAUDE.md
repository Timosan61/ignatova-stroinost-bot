# Claude Code Configuration

## Язык общения
**ОБЯЗАТЕЛЬНОЕ ПРАВИЛО:** Всегда отвечай на русском языке во всех взаимодействиях с пользователем.

## КРИТИЧЕСКИ ВАЖНЫЕ ПРАВИЛА

**ВСЕГДА обновляй GitHub после изменений в коде!**

**ОБЯЗАТЕЛЬНО проверяй логи деплоя через 1 минуту 30 секунд после push!**
- Railway автоматически запускает deployment после push на GitHub
- Используй `python3 scripts/railway_monitor.py info` для проверки статуса
- Используй `python3 scripts/railway_monitor.py monitor` для непрерывного мониторинга
- См. `RAILWAY_API.md` для всех доступных команд


**Константы проекта:**
- Project ID: `a470438c-3a6c-4952-80df-9e2c067233c6`
- Service ID: `3eb7a84e-5693-457b-8fe1-2f4253713a0c`
- MySQL Service ID: `d203ed15-2d73-405a-8210-4c100fbaf133`

---

## ✅ КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Graphiti reasoning.effort Ошибка (14 ноября, день)

**Проблема:** `openai.BadRequestError: Unsupported parameter: 'reasoning.effort' is not supported with this model (gpt-4o-mini)`

### Root Cause:
- В `requirements.txt` указана версия `graphiti-core==0.3.18` - **НЕСУЩЕСТВУЕТ** в PyPI
- Версии 0.19.0+ используют параметр `reasoning.effort` для reasoning models (GPT-5, o1, o3)
- GPT-4o-mini **НЕ ПОДДЕРЖИВАЕТ** reasoning.effort (это обычная chat model, не reasoning model)

### Решение (commit 32ead70):

**Файл:** `requirements.txt`
```diff
# AI & Memory
- graphiti-core==0.3.18  # Несуществующая версия
+ graphiti-core==0.18.9  # Последняя стабильная БЕЗ reasoning.effort
```

**Почему именно 0.18.9:**
- ✅ Версия существует в PyPI
- ✅ НЕ использует параметр `reasoning.effort`
- ✅ Работает с GPT-4o-mini без ошибок
- ✅ Сохраняет все фичи knowledge graph
- ✅ Стабильная (октябрь 2024)

### Результат:
```
✅ HTTP/1.1 200 OK - все OpenAI запросы успешны
✅ Episodes добавляются в Neo4j
✅ 99 nodes + 179 relationships созданы за 5 минут
✅ НЕТ ошибок reasoning.effort
```

### Дополнительно: Строгое ограничение на базу знаний (RAG pattern)

**Проблема:** Бот мог использовать общие знания GPT вместо базы знаний курса.

**Решение:**

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

### Версия обновлена:
- **instruction.json version:** 1.2 Strict RAG
- **Last updated:** 2025-11-14

**Commits:**
- 32ead70 - Fix: Откатить graphiti-core на 0.18.9 + строгое ограничение на базу знаний

---

## ВАЖНАЯ ЗАМЕТКА: Graphiti Dependency Conflicts (13 ноября, ночь)

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

**Порядок исправления:**
1. ❌ Deployment #1 Failed: `openai==1.54.5` incompatible with graphiti-core 0.23.1
   - Commit: d077c80 - Updated openai to >=1.91.0
2. ❌ Deployment #2 Failed: `pydantic==2.8.2` incompatible with graphiti-core 0.23.1
   - Commit: 46c7c52 - Updated pydantic to >=2.11.5
3. ❌ Deployment #3 Failed: `python-dotenv==1.0.0` incompatible with graphiti-core 0.23.1
   - Commit: 346593b - Updated python-dotenv to >=1.0.1
4. ❌ Deployment #4 Failed: Railway deployed stale code
   - Commit: 38b4bbd - Empty commit to force fresh build
5. ❌ Deployment #5 Failed: `streamlit 1.28.1` requires `tenacity<9`, but graphiti-core 0.23.1 requires `tenacity>=9.0.0`
   - Railway Error: `The conflict is caused by: graphiti-core 0.23.1 depends on tenacity>=9.0.0, streamlit 1.28.1 depends on tenacity<9`
   - Commit: 95a8507 - Updated streamlit to >=1.51.0
6. ⏳ Deployment #6 In Progress: All dependencies compatible

**Урок:** При обновлении major версий фреймворков (graphiti-core 0.12.4 → 0.23.1), всегда проверяйте requirements их зависимостей. Dependency conflicts могут быть CASCADE - один конфликт ведёт к другому.

**Commits:**
- d077c80 - Fix: openai version conflict
- 46c7c52 - Fix: pydantic version conflict
- 346593b - Fix: python-dotenv version conflict
- 38b4bbd - Trigger: Force fresh deployment
- 95a8507 - Fix: streamlit/tenacity version conflict

---

## 🔧 КРИТИЧЕСКИЕ ИСПРАВЛЕНИЯ: Graphiti Loading + GPT-4o-mini (14 ноября, утро)

### Проблемы обнаружены:

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

### Исправления:

#### ✅ 1. Переключение на GPT-4o-mini (commit 29a3d43)

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

#### ✅ 2. Исправление Checkpoint Bug (commit a388a6f)

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

### Текущий статус загрузки (14 ноября, 10:40):

**Параметры:**
- **Модель:** GPT-4o-mini (17x дешевле чем GPT-4o)
- **Entities всего:** 1,002
- **Уже загружено:** 712 (из вчерашней загрузки)
- **Осталось:** 290 entities

**Прогресс:**
```
Started:  2025-11-14 10:34:07 UTC
Progress: 25/1002 (Tier 1 завершён, Tier 2 в процессе)
Status:   is_loading: true
Errors:   0
ETA:      4-6 часов (Tier 2) + 2-3 часа (Tier 3)
```

**Важно:**
- ✅ Graphiti **сама проверяет дубликаты** - первые 712 entities пропускаются
- ✅ После entity #712 начнут добавляться новые nodes (+290)
- ⚠️ Progress счётчик обновляется только после завершения целого tier
- ⚠️ Real-time мониторинг nodes через `curl https://ignatova-stroinost-bot-production.up.railway.app/api/admin/stats`

**Стоимость:** ~$1-2 для оставшихся 290 entities

**Мониторинг:**
```bash
# Проверить статус
curl https://ignatova-stroinost-bot-production.up.railway.app/api/admin/load_status | python3 -m json.tool

# Проверить Neo4j статистику
curl https://ignatova-stroinost-bot-production.up.railway.app/api/admin/stats | python3 -m json.tool

# Автоматический мониторинг (каждые 2 минуты)
./monitor_loading.sh
```

---

## 💰 COST OPTIMIZATION: Graphiti Model Configuration (13 ноября, ночь)

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

**Локальная конфигурация (.env):**
```bash
# Graphiti LLM Configuration (cost optimization)
MODEL_NAME=gpt-4o-mini
SMALL_MODEL_NAME=gpt-4o-mini
```

**⚠️ Важно:** `.env` не коммитится в Git (содержит API keys). Переменные настраиваются **только в Railway Dashboard**.

**Документация:** https://help.getzep.com/graphiti/configuration/llm-configuration

---

## ✨ ОПТИМИЗАЦИЯ АРХИТЕКТУРЫ ПАМЯТИ (14 ноября 2025)

### 📊 Проблема: Три системы памяти работали несогласованно

**До оптимизации:**
1. **Graphiti (Neo4j)** - только база знаний курса, диалоги НЕ сохранялись
2. **MySQL** - только Business API сообщения, обычные НЕ сохранялись
3. **Zep Cloud** - и диалоги, и legacy база знаний (путаница)

**Дублирование кода:** `bot/agent.py` и `bot/core/memory.py` дублировали функционал Zep

---

### ✅ Решение: Гибридная архитектура с чётким разделением

#### 🧠 **Graphiti (Neo4j)** - Единая база знаний + Temporal knowledge graph

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

---

#### 💾 **MySQL** - Архив всех переписок для аналитики

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

---

#### ☁️ **Zep Cloud** - Только краткосрочная AI память

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

### 📋 Выполненные изменения

#### 1. ✅ Исправлено сохранение обычных сообщений в MySQL
**Файл:** `bot/handlers/message_handler.py`
- Добавлен импорт `message_storage`
- Добавлено сохранение чата и сообщений (строки 35-87)
- Поддержка голосовых сообщений с транскрипцией
- Graceful fallback при недоступности MySQL

**Результат:** Все диалоги (обычные + Business) теперь в MySQL

---

#### 2. ✅ Добавлено сохранение диалогов в Graphiti
**Файл:** `bot/agent.py`
- Добавлен вызов `add_episode()` после генерации ответа (строки 561-589)
- Episode формат: "Пользователь: {message}\nАссистент: {response}"
- Метаданные: session_id, user_name, timestamp
- Graceful fallback при недоступности Graphiti

**Результат:** Temporal knowledge graph диалогов для semantic search

---

#### 3. ✅ Удалён legacy Zep knowledge search
**Файл:** `bot/agent.py`
- Удалён блок "STRATEGY 2: Zep Cloud Search" (было: строки 212-328)
- Обновлён docstring метода `search_knowledge_base()`
- Убрана итерация по `knowledge_{category}_session_{N}`

**Результат:** Единый источник знаний - Graphiti, чистый код

---

#### 4. ✅ Рефакторинг дублирования памяти
**Файл:** `bot/core/memory.py`
- Переименован в `memory.py.deprecated`
- Функционал полностью в `bot/agent.py`

**Результат:** Один источник истины для работы с Zep

---

### 📊 Сравнение ДО/ПОСЛЕ

| Компонент | До оптимизации | После оптимизации |
|-----------|----------------|-------------------|
| **Обычные сообщения в MySQL** | ❌ НЕ сохранялись | ✅ Сохраняются |
| **Диалоги в Graphiti** | ❌ НЕ сохранялись | ✅ Сохраняются (temporal graph) |
| **База знаний** | ⚠️ Graphiti + Zep (дублирование) | ✅ Только Graphiti |
| **Semantic search по диалогам** | ❌ Нет | ✅ Через Graphiti |
| **Дублирование кода** | ⚠️ agent.py + memory.py | ✅ Только agent.py |
| **REST API для аналитики** | ⚠️ Только Business | ✅ Все диалоги |

---

### 🎯 Новая архитектура памяти (финальная)

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

### 🚀 Преимущества новой архитектуры

1. **Полное покрытие данных:**
   - Все сообщения сохраняются в MySQL (было: только Business)
   - Все диалоги сохраняются в Graphiti (было: только база знаний)

2. **Semantic search по истории:**
   - "Что мы обсуждали про возражения на прошлой неделе?"
   - Temporal reasoning через Graphiti

3. **REST API для аналитики:**
   - Все диалоги доступны через `/api/chats` (было: только Business)
   - SQL запросы для отчётов

4. **Чистый код:**
   - Один источник истины для Zep (bot/agent.py)
   - Удалён legacy Zep knowledge search
   - Нет дублирования (memory.py deprecated)

5. **Graceful degradation:**
   - MySQL недоступен → бот работает (логи warnings)
   - Graphiti недоступен → бот работает (логи warnings)
   - Zep недоступен → fallback на локальную память

---

### 📁 Изменённые файлы

1. `bot/handlers/message_handler.py` (+55 строк) - сохранение в MySQL
2. `bot/agent.py` (+28 строк, -117 строк) - Graphiti episodes + удалён Zep search
3. `bot/core/memory.py` → `memory.py.deprecated` - рефакторинг

**Commit:** `Refactor: Оптимизация архитектуры памяти - гибридный подход`

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