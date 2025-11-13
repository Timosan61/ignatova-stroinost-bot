# Neo4j & Graphiti Setup Guide

Руководство по настройке Neo4j database и Graphiti knowledge graph для бота-куратора.

## 📋 Обзор

**Graphiti** - это open-source фреймворк для построения temporal knowledge graphs, разработанный командой Zep. Мы используем его для:

- ✅ Семантического поиска по базе знаний (векторный поиск)
- ✅ Graph relationships между уроками, техниками, мозгоритмами
- ✅ Temporal reasoning (когда информация была добавлена/актуальна)
- ✅ Hybrid search (semantic + fulltext + graph traversal)

**Neo4j** - graph database, которая служит backend для Graphiti.

---

## 🚀 Быстрый старт

### Вариант 1: Neo4j Aura (Облако) - Рекомендуется

**Преимущества:**
- ✅ Managed service (не нужно настраивать сервер)
- ✅ Бесплатный tier (Free tier: 1GB storage)
- ✅ Автоматические бэкапы
- ✅ Работает сразу

**Шаги:**

1. **Создать аккаунт на Neo4j Aura**
   - Перейти на https://neo4j.com/cloud/aura/
   - Нажать "Start Free"
   - Зарегистрироваться (GitHub/Google/Email)

2. **Создать бесплатную instance**
   - Выбрать "AuraDB Free"
   - Region: ближайший к Railway servers (обычно US East)
   - Нажать "Create"

3. **Сохранить credentials**
   ```
   NEO4J_URI: neo4j+s://xxxxx.databases.neo4j.io
   NEO4J_USER: neo4j
   NEO4J_PASSWORD: <сгенерированный пароль>
   ```

   ⚠️ **ВАЖНО:** Пароль показывается только один раз! Сохраните его.

4. **Добавить credentials в Railway**
   - Railway Dashboard → Project → Variables
   - Добавить:
     ```env
     NEO4J_URI=neo4j+s://xxxxx.databases.neo4j.io
     NEO4J_USER=neo4j
     NEO4J_PASSWORD=<ваш пароль>
     GRAPHITI_ENABLED=true
     ```

5. **Проверить подключение**
   ```bash
   python scripts/test_neo4j_connection.py
   ```

   Ожидаемый вывод:
   ```
   ✅ Neo4j подключение успешно!
   ✅ Test episode добавлен!
   ```

---

### Вариант 2: Neo4j в Railway (Self-hosted)

**Преимущества:**
- ✅ Полный контроль
- ✅ Нет лимитов Free tier
- ✅ Всё в одном месте (Railway)

**Недостатки:**
- ❌ Нужно настраивать persistence (volumes)
- ❌ Стоимость Railway ($5-10/month)

**Шаги:**

1. **Добавить Neo4j плагин в Railway**
   - Railway Dashboard → Project → "New Service"
   - Database → Neo4j
   - Railway автоматически создаст переменные:
     ```env
     NEO4J_URI=neo4j://railway.internal:7687
     NEO4J_USER=neo4j
     NEO4J_PASSWORD=<автогенерированный>
     ```

2. **Настроить volume для persistence**
   - Settings → Volume
   - Mount path: `/data`
   - Size: 1GB (минимум)

3. **Добавить GRAPHITI_ENABLED**
   - Variables → Add Variable
     ```env
     GRAPHITI_ENABLED=true
     ```

4. **Проверить подключение**
   ```bash
   python scripts/test_neo4j_connection.py
   ```

---

### Вариант 3: Neo4j Desktop (Локальная разработка)

Для локальной разработки и тестирования:

1. **Скачать Neo4j Desktop**
   - https://neo4j.com/download/
   - Доступно для Windows, macOS, Linux

2. **Создать локальную database**
   - New Project → Add Database
   - Start Database

3. **Настроить .env локально**
   ```env
   NEO4J_URI=bolt://localhost:7687
   NEO4J_USER=neo4j
   NEO4J_PASSWORD=<ваш локальный пароль>
   GRAPHITI_ENABLED=true
   ```

4. **Проверить подключение**
   ```bash
   python scripts/test_neo4j_connection.py
   ```

---

## 🔧 Конфигурация

### Environment Variables

Добавьте в `.env` (локально) или Railway Variables (production):

```env
# Neo4j Database
NEO4J_URI=neo4j+s://xxxxx.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password_here

# Graphiti Feature Flag
GRAPHITI_ENABLED=true
```

### Проверка конфигурации

При старте бота вы увидите:

**Если всё настроено:**
```
✅ Graphiti Knowledge Graph включен (GRAPHITI_ENABLED=true, Neo4j configured)
```

**Если Neo4j не настроен:**
```
⚠️ Graphiti включен, но Neo4j не настроен (NEO4J_URI/NEO4J_PASSWORD не заданы)
```

**Если Graphiti отключен:**
```
❌ Graphiti Knowledge Graph отключен (GRAPHITI_ENABLED=false)
```

---

## 🧪 Тестирование

### 1. Проверка подключения

```bash
python scripts/test_neo4j_connection.py
```

Скрипт проверит:
- ✅ Environment variables
- ✅ Dependencies (graphiti-core, neo4j)
- ✅ Neo4j подключение
- ✅ Добавление test episode
- ✅ Semantic search

### 2. Просмотр данных в Neo4j Browser

**Neo4j Aura:**
- Открыть https://console.neo4j.io
- Выбрать instance → "Open with Browser"

**Neo4j Desktop:**
- Database → "Open Neo4j Browser"

**Полезные Cypher queries:**

```cypher
// Показать все nodes
MATCH (n) RETURN n LIMIT 100

// Количество episodes
MATCH (n:Episode) RETURN count(n)

// Все relationships
MATCH ()-[r]->() RETURN type(r), count(r)

// Поиск episode по содержимому
MATCH (e:Episode) WHERE e.content CONTAINS "техника" RETURN e LIMIT 10
```

---

## 📊 Архитектура

### Компоненты системы

```
┌─────────────────────────────────────┐
│         TELEGRAM BOT                │
└─────────────────────────────────────┘
              ▼
┌─────────────────────────────────────┐
│      bot/services/                  │
│    graphiti_service.py              │
│  • semantic_search()                │
│  • hybrid_search()                  │
│  • add_episode()                    │
└─────────────────────────────────────┘
              ▼
┌──────────────┐         ┌────────────┐
│   GRAPHITI   │ ◄──────►│   NEO4J    │
│  (Framework) │         │ (Database) │
└──────────────┘         └────────────┘
       ▼
┌─────────────────────────────────────┐
│      Knowledge Graph                │
│  • Lessons (60)                     │
│  • Techniques (~100)                │
│  • Student Questions (2,636)        │
│  • Curator Corrections (275)        │
│  • Brainwrite Examples (12K+)       │
└─────────────────────────────────────┘
```

### Data Flow

**Добавление knowledge:**
```
Markdown/JSON → parse_knowledge_base.py → Graphiti Episodes → Neo4j Nodes
```

**Поиск знаний:**
```
User Query → search_hybrid() → Semantic + Fulltext + Graph → Ranked Results
```

---

## 📈 Performance & Limits

### Neo4j Aura Free Tier

- **Storage**: 1GB
- **Nodes**: ~100,000-200,000 (зависит от размера)
- **RAM**: 1GB
- **Connections**: 3 concurrent

**Для нашей базы знаний:**
- 228 MB raw data
- ~10,000-15,000 nodes (после chunking)
- ~20,000-30,000 relationships
- ✅ **Влезет в Free tier!**

### Оптимизация

**Chunking strategy:**
- Разбивка больших уроков на chunks по 500-1000 токенов
- Overlap 50-100 токенов для контекста

**Индексы (создаются автоматически):**
- Vector index для semantic search
- Full-text index для keyword search

**Caching:**
- Graphiti кэширует embeddings
- Снижает cost OpenAI API

---

## 🐛 Troubleshooting

### Проблема: "Failed to initialize Graphiti service"

**Причина:** Neo4j не отвечает или credentials неверные

**Решение:**
1. Проверить NEO4J_URI в .env
2. Проверить пароль (без лишних пробелов)
3. Проверить что Neo4j instance запущена (Aura console)

### Проблема: "graphiti-core not installed"

**Решение:**
```bash
pip install graphiti-core neo4j
```

### Проблема: "Connection timeout"

**Причина:** Firewall или network issues

**Решение:**
- Проверить что Railway может достучаться до Neo4j Aura
- Добавить Railway IP в Neo4j Aura whitelist (если есть ограничения)

### Проблема: "Out of memory" (Neo4j)

**Причина:** Слишком много данных для Free tier

**Решение:**
1. Уменьшить chunking (больше размер chunks = меньше nodes)
2. Загрузить только Tier 1 данные (FAQ, основные уроки)
3. Апгрейд на Neo4j Aura Professional ($65/month)

---

## 💡 Следующие шаги

После успешной настройки Neo4j:

1. **Загрузить базу знаний** (ЭТАП 2-3)
   ```bash
   python scripts/load_knowledge_to_graphiti.py
   ```

2. **Интегрировать с ботом** (ЭТАП 4)
   - Обновить `bot/agent.py`
   - Использовать `graphiti_service.search_hybrid()`

3. **Тестирование качества** (ЭТАП 5)
   - A/B test: старый поиск vs Graphiti
   - Метрики: precision, recall, latency

---

## 📚 Дополнительные ресурсы

- **Neo4j Documentation**: https://neo4j.com/docs/
- **Graphiti GitHub**: https://github.com/getzep/graphiti
- **Graphiti Paper**: https://arxiv.org/abs/2501.13956
- **Neo4j Cypher Manual**: https://neo4j.com/docs/cypher-manual/

---

## ❓ FAQ

**Q: Можно ли использовать другую graph database вместо Neo4j?**

A: Graphiti поддерживает FalkorDB, Kuzu, Amazon Neptune. Но Neo4j - самый популярный и стабильный вариант.

**Q: Нужно ли платить за Neo4j Aura?**

A: Free tier (1GB) достаточно для текущей базы знаний. При росте (новые курсы) - нужен paid tier.

**Q: Можно ли отключить Graphiti и использовать только Zep?**

A: Да! Установите `GRAPHITI_ENABLED=false`. Бот продолжит работать с Zep Cloud для memory.

**Q: Как бэкапить Neo4j данные?**

A: Neo4j Aura - автоматические бэкапы. Self-hosted - использовать neo4j-admin dump/restore.

---

Готовы продолжить? Перейдите к [ЭТАП 2: Data Modeling](../CLAUDE.md)
