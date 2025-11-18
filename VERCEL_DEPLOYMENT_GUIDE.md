# 🚀 Руководство по деплою Telegram бота на Vercel

**Дата создания:** 18 ноября 2025
**Цель:** Миграция с Railway на Vercel Serverless
**План:** Hobby (бесплатно)
**БД:** Vercel Postgres (миграция из Railway MySQL)

---

## ✅ Подготовка выполнена

Следующие изменения уже внесены в код:

### 1. Оптимизация зависимостей
- ✅ Создан `requirements-vercel.txt` (~80 MB вместо 437 MB)
- ✅ Удалены тяжёлые библиотеки: `sentence-transformers` (~900 MB), `graphiti-core`, `supabase`, `streamlit`, `alembic`
- ✅ Добавлен `psycopg2-binary` для PostgreSQL (вместо `pymysql`)

### 2. Конфигурация Vercel
- ✅ Создан `vercel.json` с настройками serverless functions
  - maxDuration: 10s (Hobby plan)
  - memory: 1024 MB
  - excludeFiles для оптимизации bundle size
- ✅ Создан `.vercelignore` для исключения ненужных файлов

### 3. Адаптация кода
- ✅ `bot/database/database.py`: Поддержка PostgreSQL + NullPool для serverless
- ✅ `main.py`: Упрощён startup (убраны blocking retry loops)
- ✅ `bot/api/admin_endpoints.py`: Добавлен `/api/admin/setup-webhook` endpoint

---

## 📋 Пошаговая инструкция

### ШАГ 1: Создать Vercel Postgres Database

1. **Открыть Vercel Dashboard**
   ```
   https://vercel.com/dashboard
   ```

2. **Storage → Create Database → Postgres**
   - Name: `ignatova-bot-db`
   - Region: Выбрать ближайший к пользователям (например, `Frankfurt (fra1)`)

3. **Получить connection strings**
   Vercel автоматически создаст environment variables:
   ```bash
   POSTGRES_URL=postgresql://...          # Pooled connection
   POSTGRES_URL_NON_POOLING=postgresql://... # Direct connection
   POSTGRES_PRISMA_URL=postgresql://...   # Prisma (не нужен)
   ```

4. **Скопировать `POSTGRES_URL`** - она понадобится для миграции данных

---

### ШАГ 2: Мигрировать данные из Railway MySQL

#### 2.1 Экспорт из Railway MySQL

```bash
# Подключиться к Railway проекту
railway login

# Получить DATABASE_URL
railway variables

# Экспортировать данные
mysqldump -h [RAILWAY_HOST] -P [PORT] -u [USER] -p[PASSWORD] [DATABASE] > railway_backup.sql
```

**Пример:**
```bash
mysqldump -h containers-us-west-123.railway.app -P 3307 -u root -prootpassword gptifobiz > railway_backup.sql
```

#### 2.2 Адаптировать SQL для PostgreSQL

**Изменения в `railway_backup.sql`:**

1. **AUTO_INCREMENT → SERIAL:**
   ```sql
   -- MySQL
   id INT AUTO_INCREMENT PRIMARY KEY

   -- PostgreSQL
   id SERIAL PRIMARY KEY
   ```

2. **DATETIME → TIMESTAMP:**
   ```sql
   -- MySQL
   created_at DATETIME DEFAULT CURRENT_TIMESTAMP

   -- PostgreSQL
   created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
   ```

3. **LONGTEXT → TEXT:**
   ```sql
   -- MySQL
   content LONGTEXT

   -- PostgreSQL
   content TEXT
   ```

4. **Backticks → двойные кавычки:**
   ```sql
   -- MySQL
   `telegram_chats`

   -- PostgreSQL
   "telegram_chats"
   ```

5. **ENGINE=InnoDB → удалить:**
   ```sql
   -- MySQL
   ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

   -- PostgreSQL
   );
   ```

**Автоматическая конвертация (опционально):**
```bash
# Использовать sed для быстрой замены
sed -i '' 's/AUTO_INCREMENT/SERIAL/g' railway_backup.sql
sed -i '' 's/DATETIME/TIMESTAMP/g' railway_backup.sql
sed -i '' 's/LONGTEXT/TEXT/g' railway_backup.sql
sed -i '' 's/`/"/g' railway_backup.sql
sed -i '' 's/ ENGINE=InnoDB.*;//g' railway_backup.sql
```

#### 2.3 Импортировать в Vercel Postgres

```bash
# Подключиться к Vercel Postgres (используйте POSTGRES_URL из Dashboard)
psql "postgresql://user:password@hostname:5432/database"

# Импортировать адаптированный dump
\i postgres_adapted_backup.sql

# Проверить данные
\dt  # Список таблиц
SELECT COUNT(*) FROM telegram_chats;
SELECT COUNT(*) FROM telegram_messages;
```

#### 2.4 Проверить схему

Убедиться что все таблицы созданы:
```sql
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;
```

Ожидаемые таблицы:
- `telegram_chats`
- `telegram_messages`
- `graphiti_checkpoint` (если используется Graphiti)

---

### ШАГ 3: Настроить Git Repository

```bash
cd /path/to/ignatova-stroinost-bot

# Проверить текущий remote
git remote -v

# Создать новый branch для Vercel (опционально)
git checkout -b vercel-deployment

# Добавить все изменения
git add .

# Commit
git commit -m "feat: Vercel deployment configuration

- Add requirements-vercel.txt (optimized dependencies)
- Add vercel.json (serverless functions config)
- Add .vercelignore (exclude unnecessary files)
- Adapt database.py for PostgreSQL + NullPool
- Remove blocking webhook setup from startup
- Add /api/admin/setup-webhook endpoint

🚀 Ready for Vercel deployment"

# Push в GitHub
git push origin vercel-deployment
# или main:
git push origin main
```

---

### ШАГ 4: Импортировать проект в Vercel

#### 4.1 Через Vercel Dashboard

1. **New Project → Import Git Repository**
2. Выбрать GitHub repository: `ignatova-stroinost-bot`
3. **Configure Project:**
   - Framework Preset: **Other**
   - Root Directory: `.` (корень)
   - Build Command: (оставить пустым)
   - Output Directory: (оставить пустым)
   - Install Command: `pip install -r requirements-vercel.txt`

#### 4.2 Через Vercel CLI (альтернатива)

```bash
# Установить Vercel CLI
npm i -g vercel

# Login
vercel login

# Deploy
cd /path/to/ignatova-stroinost-bot
vercel --prod

# Следовать инструкциям:
# - Set up and deploy? Yes
# - Which scope? Your account
# - Link to existing project? No
# - Project name? ignatova-stroinost-bot
# - In which directory is your code located? ./
```

---

### ШАГ 5: Настроить Environment Variables

**В Vercel Dashboard → Project Settings → Environment Variables:**

#### Критические переменные (ОБЯЗАТЕЛЬНО):

```bash
# Telegram Bot
TELEGRAM_BOT_TOKEN=7790878041:AAH...
WEBHOOK_URL=https://your-project.vercel.app

# AI Services
OPENAI_API_KEY=sk-proj-...
ANTHROPIC_API_KEY=sk-ant-...
ZEP_API_KEY=z_1dWlkI...

# Knowledge Base - Qdrant Cloud
USE_QDRANT=true
QDRANT_URL=https://33d94c1b-cc7f-4b71-82cc-dcee289122f0.eu-central-1-0.aws.cloud.qdrant.io:6333
QDRANT_API_KEY=eyJhbGciOi...
QDRANT_COLLECTION=course_knowledge
EMBEDDING_MODEL=all-MiniLM-L6-v2

# Database (Vercel Postgres - автоматически создаются)
# POSTGRES_URL - уже установлен Vercel при подключении БД
# POSTGRES_URL_NON_POOLING - уже установлен

# Features
VOICE_ENABLED=true
DEBUG_INFO_ENABLED=false
SEARCH_LIMIT=10

# Vercel-specific (автоматически)
# VERCEL=1
# VERCEL_ENV=production
```

#### Опциональные переменные:

```bash
# Graphiti (если используется, но НЕ рекомендуется на Vercel)
# GRAPHITI_ENABLED=false

# Supabase (не используется)
# USE_SUPABASE=false

# Admin панель
# ADMIN_PASSWORD=your_secret_password
```

---

### ШАГ 6: Deploy

1. **Vercel автоматически запустит build** при push в main branch

2. **Проверить логи deployment:**
   ```
   Vercel Dashboard → Deployments → Latest → View Function Logs
   ```

3. **Проверить размер bundle:**
   - Должен быть < 250 MB
   - Если превышает - проверить `.vercelignore` и `excludeFiles` в `vercel.json`

4. **Получить Production URL:**
   ```
   https://your-project.vercel.app
   ```

---

### ШАГ 7: Установить Telegram Webhook

**⚠️ КРИТИЧЕСКИ ВАЖНО:** Webhook нужно установить вручную после deployment

```bash
# Вызвать endpoint для установки webhook
curl -X POST https://your-project.vercel.app/api/admin/setup-webhook

# Ожидаемый ответ:
{
  "success": true,
  "message": "Webhook set successfully",
  "webhook_url": "https://your-project.vercel.app/webhook",
  "telegram_response": {
    "ok": true,
    "result": true,
    "description": "Webhook was set"
  }
}
```

**Альтернатива (прямой вызов Telegram API):**
```bash
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
  -d "url=https://your-project.vercel.app/webhook" \
  -d "allowed_updates=[\"message\",\"business_connection\",\"business_message\"]"
```

---

### ШАГ 8: Проверить работу бота

#### 8.1 Health Check

```bash
curl https://your-project.vercel.app/health

# Ожидаемый ответ:
{
  "status": "ok",
  "ai_enabled": true,
  "ai_agent": true,
  "zep_memory": true,
  "database": "PostgreSQL",
  "environment": "Vercel Serverless"
}
```

#### 8.2 Webhook Info

```bash
curl https://your-project.vercel.app/webhook/info

# Ожидаемый ответ:
{
  "webhook_set": true,
  "url": "https://your-project.vercel.app/webhook",
  "has_custom_certificate": false,
  "pending_update_count": 0
}
```

#### 8.3 Тестовое сообщение

Отправить любое сообщение в Telegram бот:
```
Привет
```

Ожидаемый ответ:
```
Привет! [Ответ бота на основе AI]

---
🔍 DEBUG INFO:
...
```

#### 8.4 Проверить базу данных

```bash
# Проверить API stats endpoint
curl https://your-project.vercel.app/api/stats

# Должен вернуть количество записей в PostgreSQL
```

---

## ⚠️ Важные замечания

### 1. Timeout (10 секунд на Hobby plan)

**Проблема:** AI ответ может занять > 10s

**Решения:**

1. **Использовать `gpt-4o-mini` (быстрее чем GPT-4o)** - уже настроено

2. **Ограничить `max_tokens`:**
   ```python
   # В bot/agent.py (если потребуется)
   response = await openai.chat.completions.create(
       model="gpt-4o-mini",
       max_tokens=500,  # Ограничение для быстрого ответа
       ...
   )
   ```

3. **Upgrade на Vercel Pro ($20/месяц)** для 60s timeout - если необходимо

### 2. Cold Start (3-5 секунд)

**Проблема:** Первое сообщение после idle медленное

**Решения:**

1. **Использовать external healthcheck (пинговать каждые 5 минут):**
   - UptimeRobot: https://uptimerobot.com/
   - Настроить мониторинг: `GET https://your-project.vercel.app/health`
   - Интервал: 5 минут

2. **Vercel Pro prewarming** - автоматически держит функцию "тёплой"

### 3. Database Connection Limits

**Vercel Postgres Free tier:**
- 256 MB storage
- 60 hours compute per month
- Pooled connections (автоматически)

**Если превысите лимиты:**
- Upgrade на Vercel Pro ($20/месяц)
- Или оставить MySQL на Railway Standalone ($5/месяц)

### 4. Graceful Degradation

Бот работает БЕЗ базы данных (если `POSTGRES_URL` не настроен):
- ✅ AI ответы работают (Qdrant + Zep)
- ❌ Архив переписок не сохраняется
- ⚠️ Логи показывают warning, но бот функционален

---

## 🔄 Rollback Plan (если что-то пошло не так)

### Быстрый откат на Railway (< 5 минут)

1. **Переключить Telegram webhook обратно:**
   ```bash
   curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook" \
     -d "url=https://ignatova-stroinost-bot-production.up.railway.app/webhook"
   ```

2. **Railway сервис остаётся активным** (не удалять до успешной миграции)

3. **База данных Railway MySQL** - backup сохранён в `railway_backup.sql`

---

## 📊 Сравнение: Railway vs Vercel

| Параметр | Railway | Vercel Hobby |
|----------|---------|--------------|
| **Стоимость** | $20/месяц (Pro) | $0/месяц |
| **Timeout** | Unlimited | 10s |
| **Memory** | 8 GB | 1 GB |
| **Cold Start** | Minimal | 1-3s |
| **Database** | Included (MySQL) | Vercel Postgres (256 MB free) |
| **Deployment** | 2-5 минут (Docker) | 30-60 секунд |
| **Logs** | 7 дней | Real-time stream |

**Итого:** Экономия $240/год при переходе на Vercel Hobby

---

## ✅ Проверочный список после deployment

- [ ] Health check возвращает `"status": "ok"`
- [ ] Webhook установлен (`/webhook/info` возвращает `"webhook_set": true`)
- [ ] Бот отвечает на текстовые сообщения
- [ ] Голосовые сообщения транскрибируются (Whisper API)
- [ ] Knowledge base search работает (10 результатов в debug info)
- [ ] Database queries работают (`/api/stats` возвращает данные)
- [ ] Response time < 10s (проверить в Vercel Function Logs)
- [ ] Нет ошибок timeout в production логах

---

## 🆘 Troubleshooting

### Проблема 1: "Function execution timeout"

**Причина:** AI ответ занимает > 10s

**Решение:**
1. Проверить Vercel Function Logs - точное время выполнения
2. Если стабильно >10s → Upgrade на Vercel Pro ($20/месяц)
3. Или оптимизировать промпт/уменьшить `max_tokens`

### Проблема 2: "Module not found"

**Причина:** Отсутствует зависимость в `requirements-vercel.txt`

**Решение:**
1. Проверить Build Logs в Vercel
2. Добавить недостающую библиотеку в `requirements-vercel.txt`
3. Redeploy

### Проблема 3: "Database connection failed"

**Причина:** `POSTGRES_URL` не настроен или неверный

**Решение:**
1. Vercel Dashboard → Project → Settings → Environment Variables
2. Проверить что `POSTGRES_URL` присутствует
3. Если нет - создать Vercel Postgres и подключить к проекту

### Проблема 4: "Webhook not set"

**Причина:** Не вызван `/api/admin/setup-webhook`

**Решение:**
```bash
curl -X POST https://your-project.vercel.app/api/admin/setup-webhook
```

---

## 📞 Поддержка

- **Vercel Docs:** https://vercel.com/docs
- **Vercel Support:** https://vercel.com/support
- **Telegram Bot API:** https://core.telegram.org/bots/api

---

**Последнее обновление:** 18 ноября 2025
**Версия:** 1.0
**Автор:** Claude Code Migration Assistant
