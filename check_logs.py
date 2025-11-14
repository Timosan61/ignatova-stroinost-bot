#!/usr/bin/env python3
"""
Быстрая проверка логов Railway для диагностики Graphiti
"""
import os
import requests
import json
from datetime import datetime

# Загрузка токена из .env
with open('.env') as f:
    for line in f:
        if line.strip() and not line.startswith('#') and '=' in line:
            key, value = line.split('=', 1)
            os.environ[key.strip()] = value.strip()

RAILWAY_TOKEN = os.getenv('RAILWAY_TOKEN')
API_URL = 'https://backboard.railway.app/graphql/v2'

# Получить ID последнего deployment
query_deployment = """
query {
  deployments(
    input: {
      projectId: "a470438c-3a6c-4952-80df-9e2c067233c6",
      serviceId: "3eb7a84e-5693-457b-8fe1-2f4253713a0c"
    },
    first: 1
  ) {
    edges {
      node {
        id
        status
        createdAt
      }
    }
  }
}
"""

headers = {
    'Authorization': f'Bearer {RAILWAY_TOKEN}',
    'Content-Type': 'application/json',
}

# Получаем последний deployment
response = requests.post(API_URL, json={'query': query_deployment}, headers=headers)
data = response.json()

if 'data' not in data or not data['data']['deployments']['edges']:
    print("❌ Не удалось получить deployment ID")
    exit(1)

deployment_id = data['data']['deployments']['edges'][0]['node']['id']
print(f"📦 Deployment ID: {deployment_id}")
print(f"⏰ Created: {data['data']['deployments']['edges'][0]['node']['createdAt']}")
print(f"✅ Status: {data['data']['deployments']['edges'][0]['node']['status']}\n")

# Получаем логи
query_logs = f"""
query {{
  deploymentLogs(
    deploymentId: "{deployment_id}"
    limit: 200
  ) {{
    timestamp
    message
  }}
}}
"""

response = requests.post(API_URL, json={'query': query_logs}, headers=headers)
data = response.json()

if 'data' not in data or 'deploymentLogs' not in data['data']:
    print("❌ Не удалось получить логи")
    exit(1)

logs = data['data']['deploymentLogs']

# Фильтруем логи по ключевым словам
keywords = [
    'Graphiti', 'graphiti', 'Knowledge', 'knowledge',
    'search_knowledge_base', 'SUMMARY', '📊', '🔍', 
    '🎯', '✅', '📭', '🔎', 'Sources found'
]

print("=" * 80)
print("🔍 ЛОГИ СВЯЗАННЫЕ С GRAPHITI И KNOWLEDGE BASE:")
print("=" * 80)

relevant_logs = []
for log in logs:
    msg = log['message']
    if any(keyword in msg for keyword in keywords):
        relevant_logs.append(log)

if not relevant_logs:
    print("\n❌ Логи с Graphiti не найдены. Возможно:")
    print("   1. Бот ещё не получал сообщений после деплоя")
    print("   2. Отправьте тестовое сообщение боту и запустите скрипт снова\n")
    print("Показываю последние 30 общих логов:\n")
    for log in logs[-30:]:
        print(log['message'])
else:
    print(f"\n✅ Найдено {len(relevant_logs)} релевантных логов:\n")
    
    # Группируем по timestamp для лучшей читаемости
    for log in relevant_logs[-50:]:  # Последние 50
        timestamp = log.get('timestamp', '')
        if timestamp:
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                time_str = dt.strftime('%H:%M:%S')
            except:
                time_str = timestamp
        else:
            time_str = '??:??:??'
        
        msg = log['message'].strip()
        print(f"[{time_str}] {msg}")

print("\n" + "=" * 80)
print("💡 TIP: Отправьте боту сообщение и запустите снова:")
print("   python3 check_logs.py")
print("=" * 80)
