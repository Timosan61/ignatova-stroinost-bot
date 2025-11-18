#!/bin/bash

# Мониторинг прогресса миграции в Qdrant через REST API

QDRANT_URL="https://33d94c1b-cc7f-4b71-82cc-dcee289122f0.eu-central-1-0.aws.cloud.qdrant.io:6333"
QDRANT_API_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.UTJlYE3KsxYq-NCTexIE035VcMuZ5KiTAf79ezuMYgg"
COLLECTION="course_knowledge"
TOTAL_ENTITIES=980

echo "🔵 Qdrant Migration Monitor"
echo "==================================="
echo ""

while true; do
    TIMESTAMP=$(date -u '+%Y-%m-%d %H:%M:%S UTC')

    # Получить статистику collection
    RESPONSE=$(curl -s -X GET "${QDRANT_URL}/collections/${COLLECTION}" \
        -H "api-key: ${QDRANT_API_KEY}")

    POINTS_COUNT=$(echo $RESPONSE | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['result']['points_count'])")
    STATUS=$(echo $RESPONSE | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['result']['status'])")

    # Вычислить процент
    PERCENT=$(python3 -c "print(f'{$POINTS_COUNT * 100 / $TOTAL_ENTITIES:.1f}')")

    echo "[${TIMESTAMP}]"
    echo "  Points: ${POINTS_COUNT}/${TOTAL_ENTITIES} (${PERCENT}%)"
    echo "  Status: ${STATUS}"
    echo ""

    # Если загружено всё - выход
    if [ "$POINTS_COUNT" -ge "$TOTAL_ENTITIES" ]; then
        echo "✅ Migration completed!"
        break
    fi

    sleep 30
done
