# Claude Code Configuration

## Язык общения
**ОБЯЗАТЕЛЬНОЕ ПРАВИЛО:** Всегда отвечай на русском языке во всех взаимодействиях с пользователем.

## Automatic GitHub Updates Rule

**ВАЖНОЕ ПРАВИЛО:** При любых изменениях в коде бота - СРАЗУ обновлять репозиторий на GitHub.

### Процедура обновления после изменений:

1. **После любого изменения в bot/**:
   ```bash
   git add .
   git commit -m "Описание изменений"
   git push origin main
   ```

2. **Типы изменений требующих немедленного обновления:**
   - Изменения в логике бота (`bot/agent.py`, `bot/handlers.py`)
   - Обновления конфигурации (`bot/config.py`, `.env`)
   - Новые функции или исправления багов
   - Изменения в деплойменте (`deploy/`)
   - Обновления зависимостей (`requirements.txt`)

3. **Формат коммит-сообщений:**
   - Краткое описание изменений
   - Подробности что именно исправлено/добавлено
   - Обязательная подпись Claude Code

### Почему это важно:

- Railway автоматически деплоит изменения с GitHub
- Синхронизация локального кода с продакшеном
- Возможность откатить изменения при проблемах
- Команда всегда видит актуальные изменения

### Команды для быстрого обновления:

```bash
# Проверить изменения
git status
git diff

# Зафиксировать все изменения
git add .
git commit -m "Bot updates: описание изменений

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>"

# Отправить на GitHub
git push origin main
```

**ВСЕГДА обновляй GitHub после изменений в коде!**