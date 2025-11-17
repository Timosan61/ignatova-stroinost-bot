#!/bin/bash
RAILWAY_TOKEN="74a44277-c21d-4210-b0aa-38a53d8bce94"
SERVICE_ID="3eb7a84e-5693-457b-8fe1-2f4253713a0c"

echo "🔵 Включение Supabase Vector Store..."

# USE_SUPABASE=true
curl -X POST https://backboard.railway.app/graphql/v2 \
  -H "Authorization: Bearer $RAILWAY_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"query\":\"mutation { variableUpsert(input: { serviceId: \\\"$SERVICE_ID\\\", name: \\\"USE_SUPABASE\\\", value: \\\"true\\\" }) }\"}"

echo ""
echo "✅ USE_SUPABASE=true установлен!"
echo ""
echo "📋 Также установи вручную в Railway Dashboard:"
echo "   USE_QDRANT=false"
echo "   GRAPHITI_ENABLED=false"
echo ""
echo "⏳ Deployment запустится автоматически (~2 мин)"
