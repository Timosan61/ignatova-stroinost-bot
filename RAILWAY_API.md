# Railway API Documentation

## Токен доступа

**Новый Railway Token:** `74a44277-c21d-4210-b0aa-38a53d8bce94`

Этот токен сохранен в `.env` файле:
```bash
RAILWAY_TOKEN=74a44277-c21d-4210-b0aa-38a53d8bce94
```

## Использование Railway API

### 1. Bash скрипт: `scripts/railway_logs.sh`

Простой bash скрипт для базовых операций:

```bash
# Показать последние 10 deployments
./scripts/railway_logs.sh list

# Показать логи конкретного deployment
./scripts/railway_logs.sh logs 38c20d86-c4d3-458c-ada3-0fd6aad06ecd

# Показать логи последнего deployment
./scripts/railway_logs.sh logs

# Мониторинг логов в реальном времени
./scripts/railway_logs.sh monitor

# Показать переменные окружения
./scripts/railway_logs.sh env
```

### 2. Python скрипт: `scripts/railway_monitor.py`

Более функциональный Python скрипт:

```bash
# Показать последние 5 deployments
python3 scripts/railway_monitor.py list --limit 5

# Показать информацию о последнем deployment
python3 scripts/railway_monitor.py info

# Показать информацию о конкретном deployment
python3 scripts/railway_monitor.py info --id 38c20d86-c4d3-458c-ada3-0fd6aad06ecd

# Мониторинг в реальном времени (обновление каждые 10 секунд)
python3 scripts/railway_monitor.py monitor --interval 10

# Показать информацию о сервисе
python3 scripts/railway_monitor.py vars
```

### 3. Прямые curl запросы

#### Получить список deployments:

```bash
curl -s "https://backboard.railway.app/graphql/v2" \
  -H "Authorization: Bearer 74a44277-c21d-4210-b0aa-38a53d8bce94" \
  -H "Content-Type: application/json" \
  -X POST \
  -d '{
    "query": "query { deployments(input: { projectId: \"a470438c-3a6c-4952-80df-9e2c067233c6\", serviceId: \"3eb7a84e-5693-457b-8fe1-2f4253713a0c\" }, first: 5) { edges { node { id status staticUrl createdAt } } } }"
  }' | jq .
```

#### Получить информацию о конкретном deployment:

```bash
curl -s "https://backboard.railway.app/graphql/v2" \
  -H "Authorization: Bearer 74a44277-c21d-4210-b0aa-38a53d8bce94" \
  -H "Content-Type: application/json" \
  -X POST \
  -d '{
    "query": "query { deployment(id: \"078a995d-b069-4411-90f7-37182274917e\") { id status staticUrl createdAt updatedAt } }"
  }' | jq .
```

#### Получить список всех проектов:

```bash
curl -s "https://backboard.railway.app/graphql/v2" \
  -H "Authorization: Bearer 74a44277-c21d-4210-b0aa-38a53d8bce94" \
  -H "Content-Type: application/json" \
  -X POST \
  -d '{
    "query": "query { projects(first: 20) { edges { node { id name description services { edges { node { id name } } } } } } }"
  }' | jq .
```

## Константы проекта

```bash
PROJECT_ID="a470438c-3a6c-4952-80df-9e2c067233c6"
SERVICE_ID="3eb7a84e-5693-457b-8fe1-2f4253713a0c"
PROJECT_NAME="ignatova-stroinost-bot"
SERVICE_NAME="ignatova-stroinost-bot"
MYSQL_SERVICE_ID="d203ed15-2d73-405a-8210-4c100fbaf133"
API_URL="https://backboard.railway.app/graphql/v2"
```

## Статусы deployments

| Статус | Описание | Цвет |
|--------|----------|------|
| `SUCCESS` | Deployment успешен | 🟢 Зеленый |
| `FAILED` | Deployment провалился | 🔴 Красный |
| `WAITING` | Ожидает запуска | 🟡 Желтый |
| `BUILDING` | В процессе сборки | 🔵 Синий |
| `SKIPPED` | Пропущен | ⚪ Серый |

## Доступные поля Deployment

```graphql
type Deployment {
  id: ID!
  status: DeploymentStatus!
  staticUrl: String
  createdAt: DateTime!
  updatedAt: DateTime!
  canRedeploy: Boolean!
  canRollback: Boolean!
  deploymentStopped: Boolean!
  environment: Environment
  environmentId: String
  projectId: String
  service: Service
  serviceId: String
  snapshotId: String
  url: String
}
```

## Примечания

### ⚠️ Railway CLI не работает с API токеном

Railway CLI требует **интерактивного OAuth логина** и не принимает API токены:

```bash
# НЕ РАБОТАЕТ:
export RAILWAY_TOKEN=74a44277-c21d-4210-b0aa-38a53d8bce94
railway whoami  # ❌ Unauthorized

# РАБОТАЕТ:
railway login  # Открывает браузер для OAuth
```

### ✅ GraphQL API работает отлично

API токен полностью работает с GraphQL API через HTTP запросы:
- ✅ Получение списка проектов
- ✅ Получение deployments
- ✅ Информация о сервисах
- ✅ Статистика и метрики
- ❌ Build/Deploy логи (недоступны через API для токенов)

### 📊 Получение логов

**Проблема:** Railway API не предоставляет прямой доступ к build/deploy логам через GraphQL для API токенов.

**Решение:** Логи доступны только через:
1. Railway Dashboard (веб-интерфейс)
2. Railway CLI (после OAuth логина)
3. WebSocket subscription (требует специальной настройки)

**Рекомендация:** Для просмотра логов используйте Railway Dashboard:
```
https://railway.app/project/a470438c-3a6c-4952-80df-9e2c067233c6/service/3eb7a84e-5693-457b-8fe1-2f4253713a0c
```

## История токенов

| Токен | Тип | Статус | Права |
|-------|-----|--------|-------|
| `0bc5424e-585d-4761-a401-ff7443c6bd3a` | API Key (старый) | ❌ Ограничен | Только базовые query |
| `74a44277-c21d-4210-b0aa-38a53d8bce94` | Project Token (новый) | ✅ Активен | Полный доступ к проекту |

## Полезные ссылки

- **Railway GraphQL API:** https://backboard.railway.app/graphql/v2
- **Railway Dashboard:** https://railway.app/
- **Project Dashboard:** https://railway.app/project/a470438c-3a6c-4952-80df-9e2c067233c6
- **Service URL:** https://ignatova-stroinost-bot-production.up.railway.app
- **Railway Docs:** https://docs.railway.app/reference/public-api

## Примеры использования

### Проверить статус последнего deployment

```bash
python3 scripts/railway_monitor.py info
```

### Мониторить deployments в реальном времени

```bash
python3 scripts/railway_monitor.py monitor
```

### Получить список failed deployments

```bash
python3 scripts/railway_monitor.py list --limit 20 | grep FAILED
```

### Быстрая проверка доступности токена

```bash
curl -s "https://backboard.railway.app/graphql/v2" \
  -H "Authorization: Bearer 74a44277-c21d-4210-b0aa-38a53d8bce94" \
  -H "Content-Type: application/json" \
  -X POST \
  -d '{"query":"{ __schema { types { name } } }"}' | jq -r '.data.__schema.types | length'
```

Если возвращает число (например, `397`), токен работает ✅
