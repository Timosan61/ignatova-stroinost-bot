#!/bin/bash
# Update Railway Environment Variables for Supabase

RAILWAY_TOKEN="74a44277-c21d-4210-b0aa-38a53d8bce94"
SERVICE_ID="3eb7a84e-5693-457b-8fe1-2f4253713a0c"

echo "🚀 Обновление Railway environment variables..."

# Supabase URL
curl -s -X POST https://backboard.railway.app/graphql/v2 \
  -H "Authorization: Bearer $RAILWAY_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "mutation { variableUpsert(input: { serviceId: \"'$SERVICE_ID'\", name: \"SUPABASE_URL\", value: \"https://qqppsflwztnxcegcbwqd.supabase.co\" }) }"
  }' > /dev/null

echo "✅ SUPABASE_URL updated"

# Supabase Service Key
curl -s -X POST https://backboard.railway.app/graphql/v2 \
  -H "Authorization: Bearer $RAILWAY_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "mutation { variableUpsert(input: { serviceId: \"'$SERVICE_ID'\", name: \"SUPABASE_SERVICE_KEY\", value: \"sb_secret_gwZXhM-KEks3QT2DcUBvmw_B2-vCRDL\" }) }"
  }' > /dev/null

echo "✅ SUPABASE_SERVICE_KEY updated"

# Supabase Table
curl -s -X POST https://backboard.railway.app/graphql/v2 \
  -H "Authorization: Bearer $RAILWAY_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "mutation { variableUpsert(input: { serviceId: \"'$SERVICE_ID'\", name: \"SUPABASE_TABLE\", value: \"course_knowledge\" }) }"
  }' > /dev/null

echo "✅ SUPABASE_TABLE updated"

# OpenAI Embedding Model
curl -s -X POST https://backboard.railway.app/graphql/v2 \
  -H "Authorization: Bearer $RAILWAY_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "mutation { variableUpsert(input: { serviceId: \"'$SERVICE_ID'\", name: \"OPENAI_EMBEDDING_MODEL\", value: \"text-embedding-3-small\" }) }"
  }' > /dev/null

echo "✅ OPENAI_EMBEDDING_MODEL updated"

# USE_SUPABASE (initially false for testing)
curl -s -X POST https://backboard.railway.app/graphql/v2 \
  -H "Authorization: Bearer $RAILWAY_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "mutation { variableUpsert(input: { serviceId: \"'$SERVICE_ID'\", name: \"USE_SUPABASE\", value: \"false\" }) }"
  }' > /dev/null

echo "✅ USE_SUPABASE updated (set to false)"

echo ""
echo "🎉 Все переменные обновлены!"
echo "📝 Для включения Supabase установи USE_SUPABASE=true через Railway Dashboard"
