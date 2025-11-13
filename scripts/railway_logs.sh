#!/bin/bash

# Railway Logs Monitor
# Использует GraphQL API для получения логов deployment

set -e

# Загрузка токена из .env
if [ -f .env ]; then
    export $(grep -v '^#' .env | grep RAILWAY_TOKEN | xargs)
fi

if [ -z "$RAILWAY_TOKEN" ]; then
    echo "❌ RAILWAY_TOKEN не найден в .env"
    exit 1
fi

# Константы проекта
PROJECT_ID="a470438c-3a6c-4952-80df-9e2c067233c6"
SERVICE_ID="3eb7a84e-5693-457b-8fe1-2f4253713a0c"
API_URL="https://backboard.railway.app/graphql/v2"

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функция для API запросов
railway_api() {
    local query="$1"
    curl -s "$API_URL" \
        -H "Authorization: Bearer $RAILWAY_TOKEN" \
        -H "Content-Type: application/json" \
        -X POST \
        -d "{\"query\":\"$query\"}"
}

# Функция для получения списка deployments
list_deployments() {
    echo -e "${BLUE}📦 Получение последних deployments...${NC}\n"

    local response=$(railway_api "query { deployments(input: { projectId: \\\"$PROJECT_ID\\\", serviceId: \\\"$SERVICE_ID\\\" }, first: 10) { edges { node { id status staticUrl createdAt } } } }")

    echo "$response" | jq -r '.data.deployments.edges[] | .node |
        "\(.createdAt | sub("T"; " ") | sub("\\..*Z"; " UTC")) | \(.status) | \(.id)"' | while read -r line; do

        local status=$(echo "$line" | awk -F'|' '{print $2}' | xargs)
        local color=""

        case "$status" in
            "SUCCESS") color="$GREEN" ;;
            "FAILED") color="$RED" ;;
            "WAITING"|"BUILDING") color="$YELLOW" ;;
            *) color="$NC" ;;
        esac

        echo -e "${color}${line}${NC}"
    done
}

# Функция для получения логов конкретного deployment
get_deployment_logs() {
    local deployment_id="$1"

    echo -e "${BLUE}📋 Получение логов deployment: $deployment_id${NC}\n"

    local response=$(railway_api "query { deployment(id: \\\"$deployment_id\\\") { id status buildLogs } }")

    local status=$(echo "$response" | jq -r '.data.deployment.status // "UNKNOWN"')
    local logs=$(echo "$response" | jq -r '.data.deployment.buildLogs // "Логи недоступны"')

    echo -e "${YELLOW}Статус: $status${NC}\n"
    echo -e "${GREEN}Логи:${NC}"
    echo "$logs"
}

# Функция для получения последнего deployment
get_latest_deployment() {
    railway_api "query { deployments(input: { projectId: \\\"$PROJECT_ID\\\", serviceId: \\\"$SERVICE_ID\\\" }, first: 1) { edges { node { id status staticUrl createdAt } } } }" | \
        jq -r '.data.deployments.edges[0].node.id'
}

# Функция для получения переменных окружения
get_env_vars() {
    echo -e "${BLUE}🔧 Получение переменных окружения...${NC}\n"

    local response=$(railway_api "query { project(id: \\\"$PROJECT_ID\\\") { name services { edges { node { name serviceInstances { edges { node { environmentId latestDeployment { id } } } } } } } } }")

    echo "$response" | jq .
}

# Функция для мониторинга логов (обновление каждые 10 секунд)
monitor_logs() {
    local deployment_id="$1"

    if [ -z "$deployment_id" ]; then
        deployment_id=$(get_latest_deployment)
    fi

    echo -e "${GREEN}🔍 Мониторинг логов deployment: $deployment_id${NC}"
    echo -e "${YELLOW}(Обновление каждые 10 секунд, Ctrl+C для выхода)${NC}\n"

    while true; do
        clear
        get_deployment_logs "$deployment_id"
        sleep 10
    done
}

# Главное меню
case "${1:-list}" in
    list)
        list_deployments
        ;;
    logs)
        if [ -z "$2" ]; then
            deployment_id=$(get_latest_deployment)
            echo -e "${YELLOW}Используется последний deployment: $deployment_id${NC}\n"
        else
            deployment_id="$2"
        fi
        get_deployment_logs "$deployment_id"
        ;;
    monitor)
        monitor_logs "$2"
        ;;
    env)
        get_env_vars
        ;;
    *)
        echo "Railway Logs Monitor"
        echo ""
        echo "Использование:"
        echo "  $0 list                    # Показать последние 10 deployments"
        echo "  $0 logs [DEPLOYMENT_ID]    # Показать логи deployment (или последнего)"
        echo "  $0 monitor [DEPLOYMENT_ID] # Мониторинг логов в реальном времени"
        echo "  $0 env                     # Показать переменные окружения"
        echo ""
        echo "Примеры:"
        echo "  $0 list"
        echo "  $0 logs 38c20d86-c4d3-458c-ada3-0fd6aad06ecd"
        echo "  $0 monitor"
        ;;
esac
