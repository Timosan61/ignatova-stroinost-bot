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
| **Qdrant** | ✅ Работает | Semantic search (980 entities) |
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
USE_QDRANT=true              # Рекомендуется (быстрее, дешевле)
# GRAPHITI_ENABLED=true      # Альтернатива (Neo4j)

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

**Использовать Qdrant (рекомендуется):**
```bash
# Railway Dashboard → Variables
USE_QDRANT=true
GRAPHITI_ENABLED=false
```

**Использовать Graphiti:**
```bash
# Railway Dashboard → Variables
USE_QDRANT=false
GRAPHITI_ENABLED=true
```

**Инструкция:** См. `docs/QDRANT_SWITCH.md`

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
- Search latency: 30-50ms (Qdrant)
- Response time: 100-300ms (AI generation)

**База знаний:**
- Qdrant: 980 entities (25 FAQ + 127 lessons + 275 corrections + 500 questions + 53 brainwrites)
- Graphiti: 449 entities (25 FAQ + 149 lesson chunks + 275 corrections)

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
