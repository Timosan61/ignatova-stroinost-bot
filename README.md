# ignatova-stroinost-bot Bot

Автоматически созданный Telegram бот на основе Textill PRO BOT с интеграцией LLM.

## Описание

None

## Характеристики

- 🤖 **Telegram Bot API** с поддержкой Business аккаунтов  
- 🧠 **OpenAI GPT-4o** для генерации ответов
- 💾 **Zep Memory** для запоминания контекста диалогов
- 🚀 **Railway** автоматический деплой с GitHub
- 📊 **Streamlit** админ-панель для управления
- 🔗 **Webhook** режим для мгновенных ответов

## Быстрый старт

### 1. Настройка переменных окружения

Создайте файл `.env`:

```env
TELEGRAM_BOT_TOKEN=YOUR_TELEGRAM_BOT_TOKEN_HERE
BOT_USERNAME=@your_bot_username
OPENAI_API_KEY=YOUR_OPENAI_API_KEY_HERE
ZEP_API_KEY=YOUR_ZEP_API_KEY_HERE
WEBHOOK_SECRET_TOKEN=YOUR_WEBHOOK_SECRET_HERE
ADMIN_PASSWORD=YOUR_ADMIN_PASSWORD_HERE
```

### 2. Локальный запуск

```bash
# Установка зависимостей
pip install -r requirements.txt

# Запуск webhook сервера
python webhook.py

# Запуск админ-панели (отдельно)
python start_streamlit.py
```

### 3. Деплой на Railway

1. Подключите GitHub репозиторий к Railway
2. Установите переменные окружения в Railway Dashboard
3. Railway автоматически задеплоит проект

## Управление ботом

### Админ-панель

Доступна по адресу: `https://ignatova-stroinost-bot-production.up.railway.app/admin`

- 📝 Редактирование инструкций для LLM
- 📊 Мониторинг статуса деплоя  
- 🔄 Перезагрузка конфигурации
- 📈 Просмотр логов и статистики

### Основные эндпоинты

- `https://ignatova-stroinost-bot-production.up.railway.app/` - Health check
- `https://ignatova-stroinost-bot-production.up.railway.app/webhook` - Webhook для Telegram
- `https://ignatova-stroinost-bot-production.up.railway.app/webhook/set` - Установка webhook
- `https://ignatova-stroinost-bot-production.up.railway.app/debug/last-updates` - Последние обновления

## Конфигурация

### Инструкции для LLM

Инструкции хранятся в `data/instruction.json`:

```json
{
  "system_instruction": "Ваша системная инструкция...",
  "welcome_message": "Приветственное сообщение",
  "last_updated": "2025-01-27T12:00:00"
}
```

### Основные настройки

- `bot/config.py` - Конфигурация бота
- `requirements.txt` - Python зависимости  
- `Dockerfile.complete` - Docker контейнер
- `railway.json` - Настройки Railway деплоя

## Особенности

### Business API поддержка

Бот поддерживает работу с Telegram Business аккаунтами:

- Автоматическая фильтрация сообщений от владельца аккаунта
- Ответы через Business API для клиентов
- Отдельные сессии памяти для business чатов

### Память диалогов

- **Zep Cloud** для продакшн (рекомендуется)
- **Local Fallback** если Zep недоступен
- Отдельные сессии для обычных и business чатов

### Мониторинг и отладка

- Ротируемые логи в `logs/bot.log`
- Debug эндпоинты для мониторинга
- Health check для проверки статуса

## Техническая поддержка

- **GitHub**: https://github.com/USERNAME/ignatova-stroinost-bot
- **Railway**: https://railway.app/project/PROJECT_ID
- **Создано**: 2025-07-27T05:54:24.791059
- **Версия**: 1.0.0

---

*Создано автоматически системой клонирования ботов* 🤖