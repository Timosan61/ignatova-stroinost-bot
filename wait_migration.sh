#!/bin/bash

QDRANT_URL="https://33d94c1b-cc7f-4b71-82cc-dcee289122f0.eu-central-1-0.aws.cloud.qdrant.io:6333"
API_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.UTJlYE3KsxYq-NCTexIE035VcMuZ5KiTAf79ezuMYgg"
COLLECTION="course_knowledge"
TOTAL=980

echo "⏳ Мониторинг миграции в Qdrant..."
echo ""

while true; do
    TIMESTAMP=$(date '+%H:%M:%S')

    # Получить количество points
    COUNT=$(curl -s "${QDRANT_URL}/collections/${COLLECTION}" \
        -H "api-key: ${API_KEY}" \
        | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['result']['points_count'])")

    PERCENT=$(python3 -c "print(f'{${COUNT}*100/${TOTAL}:.1f}')")

    echo "[${TIMESTAMP}] Points: ${COUNT}/${TOTAL} (${PERCENT}%)"

    # Если загружено всё - выход
    if [ "$COUNT" -ge "$TOTAL" ]; then
        echo ""
        echo "✅ Миграция завершена!"
        exit 0
    fi

    sleep 30
done
