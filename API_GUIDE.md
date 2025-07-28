# 📡 API Руководство - ignatova-stroinost-bot

## 🚀 Основные Endpoints

### Статус и Мониторинг

**GET /**
- Главная страница со статусом бота
- Показывает все активные компоненты
- Список доступных endpoints

**GET /health**
- Health check для мониторинга
- Статус всех компонентов системы

### Webhook Управление

**GET /webhook/set**
- Автоматическая установка webhook
- Настройка allowed_updates для Business API

**GET /webhook/info**
- Информация о текущем webhook
- Статус подключения к Telegram

**POST /webhook**
- Основной endpoint для обработки сообщений
- Поддерживает обычные и Business сообщения
- Обработка голосовых сообщений

## 🔍 Debug Endpoints

### Память и Zep

**GET /debug/zep-status**
```json
{
  "status": "success",
  "zep_api_key_set": true,
  "zep_client_initialized": true,
  "memory_mode": "Zep Cloud"
}
```

**GET /debug/memory/{session_id}**
- Детальная информация о памяти сессии
- Последние сообщения и контекст
- Для отладки проблем с памятью

### Business API

**GET /debug/business-owners**
```json
{
  "total_connections": 2,
  "business_owners": {
    "conn_123": 987654321
  },
  "filter_active": true
}
```

### Логирование

**GET /debug/logs**
- Последние 20 строк логов
- Общая диагностика

**GET /debug/voice-logs**
- Логи голосовых сообщений
- Отладка транскрипции

## 🔧 Переменные Окружения

### Обязательные

```bash
TELEGRAM_BOT_TOKEN=ваш_токен_бота
```

### Опциональные

```bash
# AI Провайдеры
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Память
ZEP_API_KEY=z_...

# Webhook
WEBHOOK_URL=https://ваш-домен.railway.app
WEBHOOK_SECRET_TOKEN=ваш_секретный_токен
```

## 📱 Business API

### Особенности

1. **Фильтрация владельца** - сообщения от владельца Business аккаунта автоматически игнорируются
2. **Отдельные сессии** - используется префикс `business_` для session_id
3. **HTTP API отправка** - ответы отправляются через прямые HTTP запросы

### Business Connection События

```json
{
  "business_connection": {
    "id": "connection_id",
    "user": {
      "id": 123456789,
      "first_name": "Owner Name"
    },
    "is_enabled": true
  }
}
```

### Business Message События

```json
{
  "business_message": {
    "from": {
      "id": 111222333,
      "first_name": "Client"
    },
    "text": "Сообщение от клиента",
    "business_connection_id": "connection_id",
    "chat": {"id": 111222333}
  }
}
```

## 🎤 Голосовые Сообщения

### Поддерживаемые Форматы
- OGG (основной формат Telegram)
- Максимальная длительность: 10 минут
- Максимальный размер: 25MB

### Процесс Обработки
1. Получение voice сообщения через webhook
2. Загрузка аудиофайла с серверов Telegram
3. Транскрипция через OpenAI Whisper API
4. Обработка как обычное текстовое сообщение

### Требования
- OpenAI API ключ для Whisper
- Интернет подключение для загрузки файлов

## 🧠 Система Памяти

### Zep Cloud Integration

**Session ID Format:**
- Обычные сообщения: `user_{telegram_id}`
- Business сообщения: `business_{telegram_id}`

**Automatic User Management:**
- Автоматическое создание пользователей в Zep
- Метаданные: источник, время создания
- Automatic session creation

**Context Building:**
```python
# Автогенерируемый контекст + последние 6 сообщений
context = zep_context + recent_messages
```

### Local Fallback
- Если Zep недоступен → локальная память в RAM
- Ограничение: 10 последних сообщений на сессию
- Сброс при перезапуске

## 🚨 Error Handling

### Graceful Degradation

1. **Zep недоступен** → Local memory
2. **OpenAI недоступен** → Anthropic fallback  
3. **Все AI недоступно** → Простые ответы
4. **Voice недоступен** → Предложение написать текстом

### HTTP Status Codes

- `200` - Успешная обработка
- `400` - Ошибка валидации данных
- `500` - Внутренняя ошибка сервера

### Error Response Format

```json
{
  "ok": false,
  "error": "Описание ошибки",
  "action": "error_action_type"
}
```

## 📊 Мониторинг

### Health Checks

Рекомендуемые проверки:
- `GET /health` каждые 30 секунд
- `GET /debug/zep-status` каждые 5 минут
- Мониторинг логов через `/debug/logs`

### Metrics

Ключевые метрики для отслеживания:
- Response time
- Message processing rate  
- Error rate
- Memory usage
- Zep connection status

## 🔐 Безопасность

### Webhook Validation
- Secret token для проверки подлинности
- Валидация структуры сообщений
- Rate limiting (рекомендуется на уровне прокси)

### Data Privacy
- Логи не содержат персональных данных
- Zep Cloud для хранения диалогов
- Encrypted connections (HTTPS/TLS)

## 🚀 Деплой и Масштабирование

### Railway Platform
- Автоматический деплой из GitHub
- Environment variables через Dashboard
- Automatic HTTPS/custom domains

### Resource Requirements
- RAM: 512MB minimum, 1GB recommended
- CPU: 1 core sufficient для большинства нагрузок
- Storage: Minimal (статические файлы)

### Горизонтальное масштабирование
- Stateless архитектура
- Shared Zep memory
- Load balancer compatible