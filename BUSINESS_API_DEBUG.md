# 🔍 Диагностика Telegram Business API

## 📋 Проблема
Бот не отвечает через Business API, когда клиенты пишут в личные сообщения вашего Premium аккаунта.

## 🛠 Инструменты диагностики

### 1. Проверка последних updates
```
https://bot-production-472c.up.railway.app/debug/last-updates
```
Покажет последние 10 полученных webhook событий. Проверьте:
- Приходят ли `business_message` когда клиент пишет вам
- Есть ли в них `business_connection_id`

### 2. Запуск локального скрипта диагностики
```bash
python check_business_api.py
```
Проверит:
- Настройки webhook
- Разрешения бота
- Наличие business updates

### 3. Тест отправки через Business API
POST запрос на:
```
https://bot-production-472c.up.railway.app/test/business-send
```
Body:
```json
{
  "chat_id": "ID_чата",
  "business_connection_id": "ID_соединения",
  "text": "Тестовое сообщение"
}
```

## 🔍 Что проверить в Telegram

### 1. Настройки Business в Telegram
1. Откройте **Settings** → **Business** → **Chatbots**
2. Убедитесь, что:
   - Выбран правильный бот (@textilprofi_bot)
   - Включена опция "Reply to messages"
   - Настроены правильные часы работы (если используются)

### 2. Переподключение бота
1. Удалите бота из Business настроек
2. Подождите 1 минуту
3. Добавьте бота заново
4. Отправьте тестовое сообщение

### 3. Проверка Premium подписки
- Убедитесь, что Premium подписка активна
- Business функции доступны только с Premium

## 📊 Анализ логов Railway

### Что искать в логах:
1. **При получении сообщения от клиента:**
   ```
   📊 Update #X тип: business_message
   📨 Business message полная структура: {...}
   ```

2. **Значение business_connection_id:**
   ```
   📊 Business message - connection_id: 'значение'
   ```

3. **Ошибки отправки:**
   ```
   ❌ Ошибка обработки business сообщения: описание
   ```

### Возможные проблемы:

1. **Не приходят business_message**
   - Бот неправильно подключен в Business настройках
   - Webhook не получает business updates
   - Проблема с Premium подпиской

2. **business_connection_id = None**
   - Telegram не отправляет ID
   - Нужно использовать другой способ идентификации

3. **Ошибка при отправке**
   - Неверный формат business_connection_id
   - Нет прав на отправку через Business API
   - Превышен лимит сообщений

## 🚀 Дальнейшие шаги

1. **Соберите информацию:**
   - Скриншот `/debug/last-updates` после попытки клиента написать
   - Логи Railway с ошибками
   - Результат выполнения `check_business_api.py`

2. **Проверьте альтернативы:**
   - Возможно, нужно использовать `reply_to_message_id`
   - Или отправлять от имени бота, а не через Business API

3. **Обратитесь в поддержку Telegram:**
   - Если все настроено правильно, но не работает
   - Возможно, есть ограничения для вашего региона

## 📝 Временное решение

Пока Business API не работает, можно:
1. Использовать обычные ответы бота
2. Настроить автоответчик в Telegram Business
3. Использовать Quick Replies в Business настройках