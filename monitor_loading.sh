#!/bin/bash

# Скрипт мониторинга загрузки знаний в Neo4j
# Показывает прогресс каждые 2 минуты

API_URL="https://ignatova-stroinost-bot-production.up.railway.app"

echo "🔄 Мониторинг загрузки знаний в Neo4j"
echo "================================================"
echo ""

prev_nodes=0
start_time=$(date +%s)

while true; do
    # Получить статус и статистику
    status=$(curl -s "$API_URL/api/admin/load_status")
    stats=$(curl -s "$API_URL/api/admin/stats")

    # Парсинг JSON
    is_loading=$(echo $status | python3 -c "import sys, json; print(json.load(sys.stdin)['status']['is_loading'])" 2>/dev/null)
    progress=$(echo $status | python3 -c "import sys, json; print(json.load(sys.stdin)['status']['progress'])" 2>/dev/null)
    total=$(echo $status | python3 -c "import sys, json; print(json.load(sys.stdin)['status']['total'])" 2>/dev/null)
    tier=$(echo $status | python3 -c "import sys, json; print(json.load(sys.stdin)['status']['current_tier'])" 2>/dev/null)
    errors=$(echo $status | python3 -c "import sys, json; print(len(json.load(sys.stdin)['status']['errors']))" 2>/dev/null)

    nodes=$(echo $stats | python3 -c "import sys, json; print(json.load(sys.stdin)['stats']['total_nodes'])" 2>/dev/null)
    rels=$(echo $stats | python3 -c "import sys, json; print(json.load(sys.stdin)['stats']['total_relationships'])" 2>/dev/null)
    episodes=$(echo $stats | python3 -c "import sys, json; print(json.load(sys.stdin)['stats']['total_episodes'])" 2>/dev/null)

    # Проверка завершения
    if [ "$is_loading" = "False" ] || [ "$is_loading" = "false" ]; then
        echo "✅ Загрузка завершена!"
        echo ""
        echo "📊 Финальная статистика:"
        echo "   Nodes:         $nodes"
        echo "   Relationships: $rels"
        echo "   Episodes:      $episodes"
        break
    fi

    # Рассчитать скорость
    nodes_per_min=0
    if [ $prev_nodes -gt 0 ]; then
        nodes_diff=$((nodes - prev_nodes))
        nodes_per_min=$((nodes_diff / 2))  # за 2 минуты
    fi

    # Рассчитать оставшееся время
    elapsed=$(($(date +%s) - start_time))
    elapsed_min=$((elapsed / 60))

    # Прогресс
    current_time=$(date '+%H:%M:%S')
    echo "[$current_time] Progress: $progress/$total (Tier $tier) | Nodes: $nodes (+$nodes_per_min/мин) | Rels: $rels | Errors: $errors"

    prev_nodes=$nodes

    # Ждать 2 минуты
    sleep 120
done
