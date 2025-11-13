#!/bin/bash
# Мониторинг загрузки базы знаний в Neo4j через Admin API

RAILWAY_URL="https://ignatova-stroinost-bot-production.up.railway.app"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-$(grep '^ADMIN_PASSWORD=' ../.env | cut -d'=' -f2)}"

echo "🔍 Мониторинг загрузки базы знаний в Neo4j"
echo "============================================"
echo ""

# Проверка health admin API
echo "1️⃣ Проверяем доступность Admin API..."
HEALTH=$(curl -s "${RAILWAY_URL}/api/admin/health")
if echo "$HEALTH" | grep -q "admin_endpoints"; then
    echo "✅ Admin API доступен"
else
    echo "❌ Admin API недоступен"
    echo "Response: $HEALTH"
    exit 1
fi
echo ""

# Получение текущего статуса
echo "2️⃣ Текущий статус загрузки:"
STATUS=$(curl -s "${RAILWAY_URL}/api/admin/load_status")
echo "$STATUS" | jq '.' 2>/dev/null || echo "$STATUS"
echo ""

# Если загрузка не идет, предложить запустить
IS_LOADING=$(echo "$STATUS" | jq -r '.status.is_loading' 2>/dev/null)
if [ "$IS_LOADING" = "false" ] || [ "$IS_LOADING" = "null" ]; then
    echo "📊 Загрузка не запущена."
    echo ""
    echo "Для запуска используйте команду:"
    echo ""
    echo "curl -X POST '${RAILWAY_URL}/api/admin/load_knowledge' \\"
    echo "  -H 'X-Admin-Password: ${ADMIN_PASSWORD}' \\"
    echo "  -H 'Content-Type: application/json' \\"
    echo "  -d '{\"tier\": null, \"batch_size\": 50}'"
    echo ""
else
    echo "⏳ Загрузка в процессе..."

    # Показываем прогресс
    PROGRESS=$(echo "$STATUS" | jq -r '.status.progress // 0')
    TOTAL=$(echo "$STATUS" | jq -r '.status.total // 0')
    TIER=$(echo "$STATUS" | jq -r '.status.current_tier // "unknown"')
    STARTED=$(echo "$STATUS" | jq -r '.status.started_at // "unknown"')

    echo "  📈 Прогресс: ${PROGRESS}/${TOTAL}"
    echo "  🎯 Текущий tier: ${TIER}"
    echo "  🕐 Начало: ${STARTED}"
    echo ""
    echo "Повторяйте команду для обновления статуса:"
    echo "  watch -n 5 './scripts/monitor_knowledge_loading.sh'"
fi

# Статистика Neo4j
echo ""
echo "3️⃣ Статистика Neo4j:"
STATS=$(curl -s "${RAILWAY_URL}/api/admin/stats")
echo "$STATS" | jq '.' 2>/dev/null || echo "$STATS"
