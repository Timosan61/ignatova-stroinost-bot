# 🔄 MySQL → PostgreSQL Migration Guide

**Цель:** Миграция данных из Railway MySQL в Vercel Postgres
**Проект:** ignatova-stroinost-bot
**Дата:** 18 ноября 2025

---

## 📋 Предварительная подготовка

### 1. Установить необходимые инструменты

```bash
# MySQL client (для экспорта)
brew install mysql-client  # macOS
# или
sudo apt-get install mysql-client  # Linux

# PostgreSQL client (для импорта)
brew install postgresql@15  # macOS
# или
sudo apt-get install postgresql-client  # Linux
```

### 2. Получить credentials

#### Railway MySQL:
```bash
# В Railway проекте
railway login
railway variables

# Получить:
MYSQL_HOST=containers-us-west-123.railway.app
MYSQL_PORT=3307
MYSQL_USER=root
MYSQL_PASSWORD=...
MYSQL_DATABASE=gptifobiz
```

#### Vercel Postgres:
```bash
# В Vercel Dashboard → Storage → Your Database → Connection String
POSTGRES_URL=postgresql://user:password@hostname:5432/database
```

---

## ЭТАП 1: Экспорт из Railway MySQL

### 1.1 Создать директорию для backup

```bash
mkdir -p migration_backup
cd migration_backup
```

### 1.2 Экспортировать схему и данные

```bash
# Full backup (schema + data)
mysqldump \
  -h containers-us-west-123.railway.app \
  -P 3307 \
  -u root \
  -p'YOUR_PASSWORD' \
  gptifobiz \
  > railway_mysql_backup.sql

# Проверить размер файла
ls -lh railway_mysql_backup.sql
```

### 1.3 Экспортировать ТОЛЬКО схему (опционально)

```bash
# Schema only (для проверки структуры)
mysqldump \
  -h containers-us-west-123.railway.app \
  -P 3307 \
  -u root \
  -p'YOUR_PASSWORD' \
  --no-data \
  gptifobiz \
  > railway_mysql_schema.sql
```

### 1.4 Проверить backup

```bash
# Посмотреть первые 50 строк
head -n 50 railway_mysql_backup.sql

# Искать CREATE TABLE
grep "CREATE TABLE" railway_mysql_backup.sql
```

Ожидаемые таблицы:
- `telegram_chats`
- `telegram_messages`
- `graphiti_checkpoint`

---

## ЭТАП 2: Адаптация SQL для PostgreSQL

### 2.1 Автоматическая конвертация

Создать скрипт `convert_mysql_to_postgres.sh`:

```bash
#!/bin/bash

INPUT="railway_mysql_backup.sql"
OUTPUT="postgres_adapted_backup.sql"

echo "🔄 Converting MySQL dump to PostgreSQL format..."

# Копируем исходный файл
cp "$INPUT" "$OUTPUT"

# 1. AUTO_INCREMENT → SERIAL
sed -i '' 's/ AUTO_INCREMENT/ /g' "$OUTPUT"
sed -i '' 's/INT NOT NULL PRIMARY KEY/SERIAL PRIMARY KEY/g' "$OUTPUT"

# 2. DATETIME → TIMESTAMP
sed -i '' 's/DATETIME/TIMESTAMP/g' "$OUTPUT"

# 3. LONGTEXT → TEXT
sed -i '' 's/LONGTEXT/TEXT/g' "$OUTPUT"
sed -i '' 's/MEDIUMTEXT/TEXT/g' "$OUTPUT"

# 4. Backticks → двойные кавычки
sed -i '' 's/`/"/g' "$OUTPUT"

# 5. ENGINE=InnoDB → удалить
sed -i '' 's/ ENGINE=InnoDB[^;]*//g' "$OUTPUT"
sed -i '' 's/ DEFAULT CHARSET=[^;]*//g' "$OUTPUT"

# 6. DROP TABLE IF EXISTS → DROP TABLE IF EXISTS
# Уже корректно для PostgreSQL

# 7. Убрать LOCK TABLES / UNLOCK TABLES (MySQL-specific)
sed -i '' '/LOCK TABLES/d' "$OUTPUT"
sed -i '' '/UNLOCK TABLES/d' "$OUTPUT"

# 8. Убрать SET автоинкремента (MySQL-specific)
sed -i '' '/AUTO_INCREMENT=/d' "$OUTPUT"

echo "✅ Conversion complete: $OUTPUT"
echo ""
echo "⚠️  ВАЖНО: Проверьте файл вручную перед импортом!"
echo "   Особое внимание на:"
echo "   - PRIMARY KEY constraints"
echo "   - FOREIGN KEY constraints"
echo "   - INDEX definitions"
```

### 2.2 Запустить конвертацию

```bash
chmod +x convert_mysql_to_postgres.sh
./convert_mysql_to_postgres.sh
```

### 2.3 Ручная проверка адаптированного файла

```bash
# Проверить CREATE TABLE statements
grep -A 20 "CREATE TABLE" postgres_adapted_backup.sql

# Проверить что нет MySQL-specific синтаксиса
grep -i "AUTO_INCREMENT\|ENGINE=\|CHARSET=" postgres_adapted_backup.sql
# Должен вернуть пустой результат

# Проверить SERIAL columns
grep "SERIAL" postgres_adapted_backup.sql
```

### 2.4 Примеры ручных исправлений

**Пример 1: telegram_chats**

```sql
-- БЫЛО (MySQL):
CREATE TABLE `telegram_chats` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `chat_id` BIGINT NOT NULL,
  `username` VARCHAR(255),
  `first_name` VARCHAR(255),
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY `chat_id` (`chat_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- СТАЛО (PostgreSQL):
CREATE TABLE "telegram_chats" (
  "id" SERIAL PRIMARY KEY,
  "chat_id" BIGINT NOT NULL,
  "username" VARCHAR(255),
  "first_name" VARCHAR(255),
  "created_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE ("chat_id")
);
```

**Пример 2: telegram_messages**

```sql
-- БЫЛО (MySQL):
CREATE TABLE `telegram_messages` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `chat_id` INT NOT NULL,
  `telegram_message_id` BIGINT,
  `user_message` LONGTEXT,
  `bot_response` LONGTEXT,
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY `chat_id` (`chat_id`),
  FOREIGN KEY (`chat_id`) REFERENCES `telegram_chats` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB;

-- СТАЛО (PostgreSQL):
CREATE TABLE "telegram_messages" (
  "id" SERIAL PRIMARY KEY,
  "chat_id" INT NOT NULL,
  "telegram_message_id" BIGINT,
  "user_message" TEXT,
  "bot_response" TEXT,
  "created_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY ("chat_id") REFERENCES "telegram_chats" ("id") ON DELETE CASCADE
);

-- Note: INDEX создаётся отдельно в PostgreSQL
CREATE INDEX "idx_telegram_messages_chat_id" ON "telegram_messages" ("chat_id");
```

---

## ЭТАП 3: Импорт в Vercel Postgres

### 3.1 Подключиться к Vercel Postgres

```bash
# Используйте POSTGRES_URL из Vercel Dashboard
psql "postgresql://user:password@hostname:5432/database"

# Или с отдельными параметрами
psql -h hostname -p 5432 -U user -d database
```

### 3.2 Проверить текущее состояние БД

```sql
-- Список существующих таблиц
\dt

-- Если есть старые таблицы - удалить
DROP TABLE IF EXISTS telegram_messages CASCADE;
DROP TABLE IF EXISTS telegram_chats CASCADE;
DROP TABLE IF EXISTS graphiti_checkpoint CASCADE;
```

### 3.3 Импортировать адаптированный dump

```bash
# Импорт через psql
psql "postgresql://user:password@hostname:5432/database" < postgres_adapted_backup.sql

# Или внутри psql
\i postgres_adapted_backup.sql
```

**Ожидаемый вывод:**
```
CREATE TABLE
CREATE TABLE
CREATE TABLE
INSERT 0 125   (telegram_chats)
INSERT 0 4567  (telegram_messages)
CREATE INDEX
CREATE INDEX
...
```

### 3.4 Проверить импорт

```sql
-- Список таблиц
\dt

-- Должны быть:
-- telegram_chats
-- telegram_messages
-- graphiti_checkpoint

-- Количество записей
SELECT 'telegram_chats' as table_name, COUNT(*) as count FROM telegram_chats
UNION ALL
SELECT 'telegram_messages', COUNT(*) FROM telegram_messages
UNION ALL
SELECT 'graphiti_checkpoint', COUNT(*) FROM graphiti_checkpoint;

-- Проверить структуру
\d telegram_chats
\d telegram_messages

-- Примеры данных
SELECT * FROM telegram_chats LIMIT 5;
SELECT * FROM telegram_messages LIMIT 5;
```

### 3.5 Проверить SERIAL sequences

```sql
-- Проверить текущее значение sequences
SELECT last_value FROM telegram_chats_id_seq;
SELECT last_value FROM telegram_messages_id_seq;

-- Обновить sequences если нужно
SELECT setval('telegram_chats_id_seq', (SELECT MAX(id) FROM telegram_chats));
SELECT setval('telegram_messages_id_seq', (SELECT MAX(id) FROM telegram_messages));
```

---

## ЭТАП 4: Проверка корректности миграции

### 4.1 Сравнить количество записей

**MySQL (Railway):**
```sql
SELECT COUNT(*) FROM telegram_chats;   -- Например: 125
SELECT COUNT(*) FROM telegram_messages; -- Например: 4567
```

**PostgreSQL (Vercel):**
```sql
SELECT COUNT(*) FROM telegram_chats;   -- Должно быть: 125
SELECT COUNT(*) FROM telegram_messages; -- Должно быть: 4567
```

### 4.2 Проверить referential integrity

```sql
-- Проверить что все messages ссылаются на существующие chats
SELECT COUNT(*)
FROM telegram_messages m
LEFT JOIN telegram_chats c ON m.chat_id = c.id
WHERE c.id IS NULL;

-- Должно вернуть 0
```

### 4.3 Проверить индексы

```sql
-- Список индексов
\di

-- Должны быть:
-- telegram_chats_pkey (PRIMARY KEY на id)
-- telegram_chats_chat_id_key (UNIQUE на chat_id)
-- telegram_messages_pkey (PRIMARY KEY на id)
-- idx_telegram_messages_chat_id (INDEX на chat_id)
```

### 4.4 Тестовый запрос

```sql
-- Получить последние 10 сообщений с информацией о чате
SELECT
  c.chat_id,
  c.username,
  c.first_name,
  m.user_message,
  m.bot_response,
  m.created_at
FROM telegram_messages m
JOIN telegram_chats c ON m.chat_id = c.id
ORDER BY m.created_at DESC
LIMIT 10;
```

---

## ЭТАП 5: Обновить application код

### 5.1 Проверить DATABASE_URL в Vercel

В Vercel Dashboard → Project → Settings → Environment Variables:

```bash
# Должна быть автоматически установлена при подключении Postgres:
POSTGRES_URL=postgresql://...
POSTGRES_URL_NON_POOLING=postgresql://...

# Удалить старую MySQL переменную (если есть):
DATABASE_URL (удалить)
```

### 5.2 Код уже адаптирован

`bot/database/database.py` уже поддерживает:
- ✅ Автоопределение PostgreSQL vs MySQL по URL
- ✅ NullPool для Vercel serverless
- ✅ Graceful degradation если БД недоступна

### 5.3 Тестовый запуск локально (опционально)

```bash
# Установить psycopg2
pip install psycopg2-binary

# Установить POSTGRES_URL в .env
echo "POSTGRES_URL=postgresql://user:password@hostname:5432/database" > .env

# Запустить приложение
python main.py

# Проверить логи:
# ✅ Database engine created successfully: PostgreSQL @ hostname
# ⚡ Serverless mode: NullPool (new connection per request)
# ✅ База данных инициализирована и подключена
```

---

## ⚠️ Troubleshooting

### Проблема 1: "syntax error near AUTO_INCREMENT"

**Причина:** Не все вхождения `AUTO_INCREMENT` были заменены

**Решение:**
```bash
# Найти оставшиеся вхождения
grep -n "AUTO_INCREMENT" postgres_adapted_backup.sql

# Заменить вручную или повторить sed команду
```

### Проблема 2: "column type does not match"

**Причина:** Неправильная конвертация типов данных

**Решение:**
```sql
-- Проверить типы столбцов
\d tablename

-- Исправить вручную:
ALTER TABLE tablename ALTER COLUMN columnname TYPE new_type;
```

### Проблема 3: "duplicate key value violates unique constraint"

**Причина:** Sequence не синхронизирована с MAX(id)

**Решение:**
```sql
-- Обновить sequence
SELECT setval('tablename_id_seq', (SELECT MAX(id) FROM tablename));
```

### Проблема 4: "connection refused"

**Причина:** Неверный POSTGRES_URL или firewall

**Решение:**
1. Проверить URL в Vercel Dashboard
2. Убедиться что IP не заблокирован
3. Использовать `POSTGRES_URL_NON_POOLING` для direct connection

---

## 📊 Checklist после миграции

- [ ] Все таблицы созданы в PostgreSQL
- [ ] Количество записей совпадает (MySQL vs PostgreSQL)
- [ ] PRIMARY KEY constraints установлены
- [ ] FOREIGN KEY constraints работают
- [ ] UNIQUE constraints установлены
- [ ] Indexes созданы
- [ ] Sequences синхронизированы с MAX(id)
- [ ] Referential integrity проверена (нет orphan records)
- [ ] Тестовый запрос возвращает корректные данные
- [ ] Application подключается к PostgreSQL (логи без ошибок)
- [ ] CRUD операции работают (CREATE, READ, UPDATE, DELETE)

---

## 🔐 Backup и Rollback

### Создать backup PostgreSQL

```bash
# Full backup
pg_dump "postgresql://user:password@hostname:5432/database" > vercel_postgres_backup.sql

# Schema only
pg_dump --schema-only "postgresql://..." > vercel_postgres_schema.sql

# Data only
pg_dump --data-only "postgresql://..." > vercel_postgres_data.sql
```

### Rollback на Railway MySQL

Если миграция неудачна:

1. **Восстановить из backup:**
   ```bash
   mysql -h railway-host -P 3307 -u root -p database < railway_mysql_backup.sql
   ```

2. **Переключить application:**
   ```bash
   # В Vercel Environment Variables
   # Удалить POSTGRES_URL
   # Добавить DATABASE_URL (MySQL)
   ```

3. **Redeploy на Vercel**

---

## 📞 Дополнительная информация

### PostgreSQL vs MySQL - ключевые различия

| Фича | MySQL | PostgreSQL |
|------|-------|------------|
| Auto-increment | `AUTO_INCREMENT` | `SERIAL`, `BIGSERIAL` |
| Datetime | `DATETIME` | `TIMESTAMP`, `TIMESTAMPTZ` |
| Text | `LONGTEXT`, `MEDIUMTEXT` | `TEXT` (unlimited) |
| Quotes | Backticks \` | Double quotes " |
| Case sensitivity | Case-insensitive (default) | Case-sensitive |
| Boolean | `TINYINT(1)` | `BOOLEAN` |
| Transactions | InnoDB engine required | Built-in ACID |

### Useful PostgreSQL commands

```sql
-- Show all tables
\dt

-- Describe table
\d tablename

-- Show indexes
\di

-- Show constraints
\d+ tablename

-- Show sequences
\ds

-- Current database size
SELECT pg_size_pretty(pg_database_size(current_database()));

-- Table size
SELECT pg_size_pretty(pg_total_relation_size('tablename'));
```

---

**Последнее обновление:** 18 ноября 2025
**Версия:** 1.0
**Автор:** Claude Code Migration Assistant
