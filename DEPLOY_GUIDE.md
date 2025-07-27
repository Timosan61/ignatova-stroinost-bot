# 🚀 Пошаговое руководство по деплою Artyom Integrator

## Обзор архитектуры

Artyom Integrator состоит из двух компонентов:
1. **Основной бот** - webhook сервер (webhook.py) 
2. **Streamlit админка** - веб-интерфейс для управления (admin/)

Оба компонента деплоятся на Railway как отдельные сервисы и автоматически обновляются при push в GitHub.

## 🔧 Шаг 1: Создание Railway проектов

### Основной бот (artyom-integrator-bot)

1. Войдите в [Railway.app](https://railway.app)
2. Нажмите **"New Project"**
3. Выберите **"Deploy from GitHub repo"**
4. Подключите репозиторий `artem.integrator`
5. **Важно:** В настройках проекта укажите:
   - **Service Name**: `artyom-integrator-bot`
   - **Railway config file**: `railway.json`
   - **Root directory**: `.` (корень проекта)

### Streamlit админка (artyom-integrator-admin)

1. В том же Railway аккаунте создайте **второй проект**
2. Также подключите репозиторий `artem.integrator`
3. **Важно:** В настройках проекта укажите:
   - **Service Name**: `artyom-integrator-admin`
   - **Railway config file**: `railway-streamlit.json`
   - **Root directory**: `.` (корень проекта)

## 🔑 Шаг 2: Настройка переменных окружения

### Для основного бота (artyom-integrator-bot):

Перейдите в **Variables** и добавьте:

```bash
TELEGRAM_BOT_TOKEN=[ваш_токен_от_botfather]
WEBHOOK_SECRET_TOKEN=artyom_integrator_secret_2025
BOT_USERNAME=artyom_integrator_bot
OPENAI_API_KEY=[ваш_openai_ключ]
ZEP_API_KEY=[ваш_zep_ключ]
```

### Для Streamlit админки (artyom-integrator-admin):

```bash
ADMIN_PASSWORD=secure_admin_password_2025
```

## 🌐 Шаг 3: Получение URL и проверка

После деплоя Railway предоставит URL:
- **Основной бот**: `https://artyom-integrator-bot-production.up.railway.app`
- **Админка**: `https://artyom-integrator-admin-production.up.railway.app`

### Проверка основного бота:

1. Откройте `https://artyom-integrator-bot-production.up.railway.app/`
2. Должно показать статус: `🟢 ONLINE`
3. Проверьте `ai_status: "✅ ENABLED"`

### Установка webhook:

Перейдите по ссылке: `https://artyom-integrator-bot-production.up.railway.app/webhook/set`

## 📱 Шаг 4: Настройка Telegram Business

1. Откройте **Telegram Settings → Business → Chatbots**
2. Найдите и выберите **@artyom_integrator_bot**
3. Включите **"Reply to messages"**
4. Теперь бот будет отвечать от вашего имени как Елена из Textile Pro

## 🔄 Автоматическое обновление

Система настроена на автоматический деплой. При любых изменениях:

```bash
git add .
git commit -m "Update: описание изменений

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>"
git push origin main
```

**Railway автоматически:**
1. Обнаружит изменения в GitHub
2. Пересоберет Docker образы
3. Переразвернет оба сервиса
4. Обновит webhook URL

## 🧪 Тестирование

### Проверка основного функционала:

1. Отправьте `/start` боту - должно прийти приветствие от Елены
2. Задайте вопрос о производстве одежды - должен прийти AI ответ
3. Проверьте работу через Business API (отправьте сообщение в личные сообщения)

### Проверка админки:

1. Откройте Streamlit админку
2. Введите пароль
3. Проверьте статус бота
4. Попробуйте обновить инструкции

## 📊 Мониторинг

### Endpoints для мониторинга:

- **Health check**: `/`
- **Webhook status**: `/webhook/info`
- **Last updates**: `/debug/last-updates`
- **Memory status**: `/debug/zep-status`
- **Prompt status**: `/debug/prompt`

### Логи Railway:

1. Откройте проект в Railway
2. Перейдите в **Deployments**
3. Нажмите на активный деплой
4. Смотрите логи в реальном времени

## 🆘 Устранение проблем

### Бот не отвечает:

1. Проверьте health check endpoint
2. Проверьте переменные окружения
3. Проверьте логи Railway
4. Переустановите webhook через `/webhook/set`

### Ошибки AI:

1. Проверьте `OPENAI_API_KEY`
2. Проверьте `/debug/prompt` endpoint
3. Перезагрузите промпт через админку

### Проблемы с памятью:

1. Проверьте `ZEP_API_KEY`
2. Проверьте `/debug/zep-status`
3. Память работает в fallback режиме если Zep недоступен

## ✅ Контрольный список

- [ ] Создан проект для основного бота в Railway
- [ ] Создан проект для Streamlit админки в Railway
- [ ] Настроены все переменные окружения
- [ ] Получены URL для обоих сервисов
- [ ] Установлен webhook
- [ ] Настроен Telegram Business
- [ ] Протестирован основной функционал
- [ ] Проверена админка
- [ ] Настроен автоматический деплой из GitHub

## 🎉 Готово!

После выполнения всех шагов у вас будет:
- ✅ Автоматически работающий Artyom Integrator
- ✅ Консультант Елена отвечает клиентам от вашего имени
- ✅ Веб-админка для управления
- ✅ Автоматический деплой при изменениях
- ✅ Полный мониторинг и логирование