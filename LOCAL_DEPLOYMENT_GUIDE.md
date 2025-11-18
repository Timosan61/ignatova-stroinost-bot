# Руководство по локальному развёртыванию бота

**Дата:** 2025-11-17
**Статус:** 🟡 Частично готов (ожидает действительный ngrok authtoken)

---

## 📊 Текущий статус

### ✅ Выполнено

| Задача | Статус | Файл/Команда |
|--------|--------|--------------|
| ngrok установлен | ✅ | `/home/coder/.local/bin/ngrok` |
| ngrok authtoken настроен | ✅ | `/home/coder/.config/ngrok/ngrok.yml` |
| systemd service для ngrok | ✅ | `~/.config/systemd/user/ignatova-bot-ngrok.service` |
| systemd service для бота | ✅ | `~/.config/systemd/user/ignatova-bot.service` |
| .env обновлён | ✅ | `USE_SUPABASE=true`, `GRAPHITI_ENABLED=false` |
| Supabase данные загружены | ✅ | 3,234 entities ($0.02) |

### ❌ Заблокировано

| Проблема | Причина | Решение |
|----------|---------|---------|
| ngrok authtoken недействителен | `ERR_NGROK_107` | Получить новый токен с https://dashboard.ngrok.com/get-started/your-authtoken |

**Текущий (недействительный) токен:**
`35cX47oYvjiRSKoz6fbXplfowee_6iJUBVBokYnnhGympBFNq`

---

## 🚀 Шаги для завершения развёртывания

### 1. Получить действительный ngrok authtoken

**Шаг 1.1:** Открой https://dashboard.ngrok.com/get-started/your-authtoken

**Шаг 1.2:** Скопируй новый authtoken (формат: `2abC...xyz`)

**Шаг 1.3:** Обнови конфигурацию ngrok:

```bash
/home/coder/.local/bin/ngrok config add-authtoken YOUR_NEW_TOKEN_HERE
```

**Проверка:**
```bash
cat /home/coder/.config/ngrok/ngrok.yml
# Должен показать новый токен
```

---

### 2. Запустить ngrok сервис

```bash
# Перезагрузить systemd
systemctl --user daemon-reload

# Запустить ngrok
systemctl --user start ignatova-bot-ngrok.service

# Проверить статус
systemctl --user status ignatova-bot-ngrok.service
```

**Ожидаемый результат:**
```
● ignatova-bot-ngrok.service - ngrok tunnel for Ignatova Bot
   Active: active (running)
```

---

### 3. Получить публичный ngrok URL

```bash
# Подождать 3 секунды для инициализации ngrok
sleep 3

# Получить URL через ngrok API
curl -s http://localhost:4040/api/tunnels | python3 -m json.tool
```

**Пример вывода:**
```json
{
  "tunnels": [{
    "public_url": "https://1234-56-78-90-12.ngrok-free.app",
    "proto": "https",
    "config": {
      "addr": "http://localhost:8000"
    }
  }]
}
```

**Скопируй** `public_url` (например: `https://1234-56-78-90-12.ngrok-free.app`)

---

### 4. Обновить WEBHOOK_URL в .env

```bash
# Пример (ЗАМЕНИ на твой реальный ngrok URL!)
cd /home/coder/projects/bot_cloning_railway/clones/ignatova-stroinost-bot

# Способ 1: Вручную отредактировать
nano .env
# Найти строку: WEBHOOK_URL=https://ignatova-stroinost-bot-production.up.railway.app
# Заменить на: WEBHOOK_URL=https://ТВОЙ-NGROK-URL.ngrok-free.app

# Способ 2: Через sed (автоматически, но ОСТОРОЖНО!)
# sed -i 's|WEBHOOK_URL=.*|WEBHOOK_URL=https://ТВОЙ-NGROK-URL.ngrok-free.app|' .env
```

**Проверка:**
```bash
grep WEBHOOK_URL .env
# Должен показать твой ngrok URL
```

---

### 5. Запустить бот локально через systemd

```bash
# Включить автозапуск при старте системы
systemctl --user enable ignatova-bot-ngrok.service
systemctl --user enable ignatova-bot.service

# Запустить бот
systemctl --user start ignatova-bot.service

# Проверить статус
systemctl --user status ignatova-bot.service
```

**Ожидаемый результат:**
```
● ignatova-bot.service - Ignatova Stroinost Bot (Telegram + Supabase)
   Active: active (running)
```

**Проверка логов:**
```bash
# Логи бота
journalctl --user -u ignatova-bot.service -f

# Логи ngrok
journalctl --user -u ignatova-bot-ngrok.service -f
```

---

### 6. Установить webhook на Telegram

```bash
# ЗАМЕНИ на твой ngrok URL!
NGROK_URL="https://ТВОЙ-NGROK-URL.ngrok-free.app"
BOT_TOKEN="7790878041:AAHfOEF3tWIeEtMDsrkPVtCWZLH8Uml-xzs"

curl -X POST "https://api.telegram.org/bot${BOT_TOKEN}/setWebhook" \
  -H "Content-Type: application/json" \
  -d "{
    \"url\": \"${NGROK_URL}/webhook\",
    \"allowed_updates\": [\"message\", \"business_connection\", \"business_message\"]
  }"
```

**Ожидаемый ответ:**
```json
{
  "ok": true,
  "result": true,
  "description": "Webhook was set"
}
```

**Проверка webhook:**
```bash
curl "https://api.telegram.org/bot${BOT_TOKEN}/getWebhookInfo" | python3 -m json.tool
```

**Должен показать:**
```json
{
  "ok": true,
  "result": {
    "url": "https://ТВОЙ-NGROK-URL.ngrok-free.app/webhook",
    "has_custom_certificate": false,
    "pending_update_count": 0
  }
}
```

---

### 7. Протестировать бота

**Шаг 7.1:** Открой Telegram бота: @ignatova_stroinost_bot_bot

**Шаг 7.2:** Отправь тестовый вопрос:
```
как мне есть что хочу и не толстеть?
```

**Шаг 7.3:** Проверь DebugInfo в ответе:
```
🔍 DEBUG INFO:
🟣 Search System: SUPABASE Vector DB        ← Должен быть SUPABASE!
📚 Knowledge Base: ✅ Использована
📊 Results: X найдено
⭐ Avg Relevance: 0.XX
📁 Entity Types: lesson, faq, correction...
```

**Если показывает `QDRANT` или `FALLBACK`:**
❌ Бот не перезагрузил .env → перезапусти сервис:
```bash
systemctl --user restart ignatova-bot.service
```

---

### 8. Остановить Railway deployment

**После успешного тестирования:**

```bash
# Через Railway CLI (если установлен)
railway down

# ИЛИ через Railway Dashboard:
# 1. Открой https://railway.app
# 2. Найди проект: ignatova-stroinost-bot-production
# 3. Settings → Pause Deployment
```

**ВАЖНО:**
⚠️ НЕ удаляй Railway проект! Оставь паузу на случай необходимости возврата.

---

## 🔧 Конфигурация

### .env файл

**Актуальные настройки:**

```bash
# Supabase Vector Store (АКТИВЕН)
SUPABASE_URL=https://qqppsflwztnxcegcbwqd.supabase.co
SUPABASE_SERVICE_KEY=sb_secret_gwZXhM-KEks3QT2DcUBvmw_B2-vCRDL
SUPABASE_TABLE=course_knowledge
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
USE_SUPABASE=true                           # ← ВКЛЮЧЕН!

# Graphiti (ОТКЛЮЧЕН)
GRAPHITI_ENABLED=false                      # ← ВЫКЛЮЧЕН!

# Webhook (ТРЕБУЕТ ОБНОВЛЕНИЯ!)
WEBHOOK_URL=https://ТВОЙ-NGROK-URL.ngrok-free.app  # ← ОБНОВИ!
```

### systemd services

**Расположение:**
- `~/.config/systemd/user/ignatova-bot-ngrok.service`
- `~/.config/systemd/user/ignatova-bot.service`

**Зависимости:**
```
ignatova-bot.service
└── Requires: ignatova-bot-ngrok.service  # Бот зависит от ngrok
```

**Логи:**
```bash
# Все логи бота
journalctl --user -u ignatova-bot.service -f

# Все логи ngrok
journalctl --user -u ignatova-bot-ngrok.service -f

# Объединённые логи
journalctl --user -u ignatova-bot.service -u ignatova-bot-ngrok.service -f
```

---

## 🔍 Диагностика проблем

### Проблема: ngrok authtoken недействителен

**Симптом:**
```
ERR_NGROK_107: authentication failed
```

**Решение:**
1. Открой https://dashboard.ngrok.com/get-started/your-authtoken
2. Скопируй новый токен
3. Обнови: `ngrok config add-authtoken NEW_TOKEN`
4. Перезапусти: `systemctl --user restart ignatova-bot-ngrok.service`

---

### Проблема: Бот не отвечает

**Шаг 1:** Проверь статус сервисов:
```bash
systemctl --user status ignatova-bot-ngrok.service
systemctl --user status ignatova-bot.service
```

**Шаг 2:** Проверь логи:
```bash
journalctl --user -u ignatova-bot.service -n 50 --no-pager
```

**Шаг 3:** Проверь webhook:
```bash
BOT_TOKEN="7790878041:AAHfOEF3tWIeEtMDsrkPVtCWZLH8Uml-xzs"
curl "https://api.telegram.org/bot${BOT_TOKEN}/getWebhookInfo"
```

**Шаг 4:** Проверь health endpoint:
```bash
NGROK_URL="https://ТВОЙ-NGROK-URL.ngrok-free.app"
curl "${NGROK_URL}/health"
```

---

### Проблема: Бот использует Qdrant вместо Supabase

**Симптом:**
```
Search System: QDRANT Vector DB
```

**Решение:**
```bash
# 1. Проверь .env
grep USE_SUPABASE .env
# Должен показать: USE_SUPABASE=true

grep GRAPHITI_ENABLED .env
# Должен показать: GRAPHITI_ENABLED=false

# 2. Перезапусти бот
systemctl --user restart ignatova-bot.service

# 3. Проверь логи при старте
journalctl --user -u ignatova-bot.service -n 100 --no-pager | grep -i "supabase\|qdrant\|graphiti"
```

---

## 📋 Полный чеклист

- [ ] 1. Получить действительный ngrok authtoken
- [ ] 2. Обновить ngrok config: `ngrok config add-authtoken TOKEN`
- [ ] 3. Запустить ngrok: `systemctl --user start ignatova-bot-ngrok.service`
- [ ] 4. Получить ngrok URL: `curl http://localhost:4040/api/tunnels`
- [ ] 5. Обновить WEBHOOK_URL в .env
- [ ] 6. Запустить бот: `systemctl --user start ignatova-bot.service`
- [ ] 7. Установить Telegram webhook
- [ ] 8. Протестировать в Telegram (проверить DebugInfo)
- [ ] 9. Остановить Railway deployment (после успешного теста)

---

## 🛠️ Полезные команды

```bash
# Просмотр всех user systemd сервисов
systemctl --user list-units --type=service

# Перезагрузка systemd после изменения .service файлов
systemctl --user daemon-reload

# Включить автозапуск
systemctl --user enable ignatova-bot-ngrok.service
systemctl --user enable ignatova-bot.service

# Остановить всё
systemctl --user stop ignatova-bot.service
systemctl --user stop ignatova-bot-ngrok.service

# Запустить всё
systemctl --user start ignatova-bot-ngrok.service
systemctl --user start ignatova-bot.service

# Статус всех сервисов
systemctl --user status ignatova-bot*

# Логи в реальном времени (оба сервиса)
journalctl --user -u ignatova-bot-ngrok.service -u ignatova-bot.service -f
```

---

## 📞 Следующие шаги

**Сейчас:** Жду действительный ngrok authtoken для продолжения.

**После получения токена:** Выполни шаги 1-9 из чеклиста выше.

**Если возникнут проблемы:** Проверь раздел "Диагностика проблем".

---

**Обновлено:** 2025-11-17 20:15 UTC
**Автор:** Claude Code (Local Deployment Setup)
