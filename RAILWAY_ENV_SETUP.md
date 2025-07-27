# 🚀 Настройка переменных окружения для Artyom Integrator

## 📋 Обязательные переменные окружения для Railway

Добавьте эти переменные в Railway Dashboard → Variables:

### 1. **TELEGRAM_BOT_TOKEN**
```
[ВАШ_ТОКЕН_БОТА_ОТ_BOTFATHER]
```
Токен вашего бота от @BotFather

### 2. **WEBHOOK_SECRET_TOKEN**
```
artyom_integrator_secret_2025
```
Секретный токен для безопасности webhook

### 3. **BOT_USERNAME**
```
artyom_integrator_bot
```
Имя вашего бота без @

### 4. **OPENAI_API_KEY** (для AI ответов)
```
[ВАШ_OPENAI_API_КЛЮЧ]
```
Ключ OpenAI для генерации умных ответов (получите на platform.openai.com)

### 5. **ZEP_API_KEY** (для памяти диалогов)
```
[ВАШ_ZEP_API_КЛЮЧ]
```
Ключ Zep для сохранения контекста разговоров

### 6. **WEBHOOK_URL** (опционально)
```
https://artyom-integrator-production.up.railway.app/webhook
```
URL webhook (Railway автоматически подставит правильный домен)

## 🔧 Как добавить переменные:

1. Откройте ваш проект в Railway
2. Перейдите в раздел **Variables**
3. Нажмите **New Variable**
4. Добавьте каждую переменную:
   - Name: `TELEGRAM_BOT_TOKEN`
   - Value: вставьте значение
5. Повторите для всех переменных
6. Railway автоматически перезапустит приложение

## ✅ После настройки:

1. **Проверьте статус:**
   ```
   https://artyom-integrator-production.up.railway.app/
   ```
   Должно показать:
   - `ai_status: "✅ ENABLED"`
   - `openai_configured: true`

2. **Установите webhook:**
   ```
   https://artyom-integrator-production.up.railway.app/webhook/set
   ```

3. **Протестируйте бота:**
   - Отправьте `/start` - должно прийти AI приветствие от Елены
   - Задайте вопрос о производстве одежды - должен прийти умный ответ

## 🤖 Что дает каждый компонент:

- **OpenAI** - умные ответы на вопросы пользователей от имени Елены
- **Zep** - память диалогов, бот помнит предыдущие разговоры
- **Webhook** - мгновенные ответы без задержек
- **Business API** - работа через ваш Premium аккаунт

## 📊 Проверка работы Zep:

После нескольких сообщений бот будет:
- Помнить имя пользователя
- Учитывать контекст предыдущих вопросов
- Давать персонализированные ответы от имени Елены

## 🆘 Если что-то не работает:

1. Проверьте логи в Railway Dashboard
2. Убедитесь что все переменные добавлены правильно
3. Проверьте endpoint `/webhook/info`
4. Переустановите webhook через `/webhook/set`

## 🔄 Автоматическое обновление:

После изменений в коде просто сделайте:
```bash
git add .
git commit -m "Update Artyom integrator"
git push origin main
```

Railway автоматически пересоберет и переразвернет приложение.