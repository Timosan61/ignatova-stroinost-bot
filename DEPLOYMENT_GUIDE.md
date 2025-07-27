# 🚀 Руководство по деплою Telegram Business Bot

## Что было сделано

✅ **Созданы файлы для webhook:**
- `bot/business_handlers.py` - обработчики Business API событий
- `bot/webhook_server.py` - FastAPI сервер для webhook (исправлены async методы)
- `Dockerfile.webhook` - Docker-контейнер для webhook сервера
- `start_webhook.py` - скрипт запуска webhook сервера

✅ **Настроена конфигурация Railway:**
- `deploy/railway.json` - обновлен для webhook сервера
- `deploy/.env.railway` - переменные окружения с инструкциями

## Инструкции по деплою

### 1. Загрузка кода в GitHub
```bash
git add .
git commit -m "Add Telegram Business API webhook support

- Created business_handlers.py for Business API events
- Added webhook_server.py with FastAPI integration
- Updated railway.json for webhook deployment
- Fixed async/await issues with pyTelegramBotAPI

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>"
git push origin main
```

### 2. Настройка переменных в Railway Dashboard

Перейдите в Railway Dashboard → Variables и добавьте:

#### Обязательные переменные:
- `TELEGRAM_BOT_TOKEN` = ваш токен бота от @BotFather
- `WEBHOOK_SECRET_TOKEN` = `textil_pro_business_secret_2025`
- `BOT_USERNAME` = имя вашего бота (например `textilprofi_bot`)
- `OPENAI_API_KEY` = ваш API ключ OpenAI

#### Опциональные переменные:
- `ZEP_API_KEY` = ваш ZEP ключ для памяти

### 3. После деплоя Railway

Railway автоматически:
- ✅ Создаст HTTPS домен (например: `https://textil-pro-bot-production.up.railway.app`)
- ✅ Установит SSL сертификат
- ✅ Запустит webhook сервер на порту из переменной `PORT`

### 4. Настройка webhook в Telegram

После деплоя вызовите API для установки webhook:

```bash
# Вариант 1: Через ваш сайт
curl -X POST "https://your-railway-domain.up.railway.app/webhook/set"

# Вариант 2: Напрямую через Telegram API
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://your-railway-domain.up.railway.app/webhook",
    "secret_token": "textil_pro_business_secret_2025",
    "allowed_updates": ["message", "edited_message", "callback_query", "business_connection", "business_message", "edited_business_message", "deleted_business_messages"]
  }'
```

### 5. Проверка работы

1. **Health check:** `GET https://your-railway-domain.up.railway.app/`
2. **Webhook info:** `GET https://your-railway-domain.up.railway.app/webhook/info`
3. **Отправьте сообщение боту** через ваш Telegram Premium аккаунт

## Как работает Business API

1. **Business Connection:** Бот подключается к вашему Premium аккаунту
2. **Business Messages:** Сообщения от клиентов приходят как `business_message` события
3. **Webhook Response:** Бот отвечает через `business_connection_id`
4. **HTTPS Required:** Telegram требует валидный SSL (Railway предоставляет)

## Troubleshooting

### Проблема: Webhook не устанавливается
- Проверьте что домен Railway доступен по HTTPS
- Убедитесь что `WEBHOOK_SECRET_TOKEN` правильно настроен

### Проблема: Бот не отвечает на business сообщения
- Проверьте логи Railway
- Убедитесь что ваш Premium аккаунт подключен к боту
- Проверьте что `business_connection_id` передается правильно

### Проблема: SSL ошибки
- Railway автоматически выдает SSL, подождите несколько минут после деплоя
- Проверьте что используете правильный Railway домен

## Команды для управления

```bash
# Удалить webhook (вернуться к polling)
curl -X DELETE "https://your-railway-domain.up.railway.app/webhook"

# Проверить статус webhook
curl "https://your-railway-domain.up.railway.app/webhook/info"

# Health check
curl "https://your-railway-domain.up.railway.app/"
```

## 🎉 Готово!

После выполнения всех шагов ваш бот будет:
- ✅ Работать через webhook (быстрее polling)
- ✅ Обрабатывать Business API события
- ✅ Отвечать через ваш Premium аккаунт
- ✅ Иметь HTTPS и валидный SSL
- ✅ Автоматически деплоиться при изменениях в GitHub