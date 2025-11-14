#!/usr/bin/env python3
"""
Проверка Zep Cloud памяти для конкретного пользователя
"""
import os
import requests
import json

# Загрузка токена из .env
with open('.env') as f:
    for line in f:
        if line.strip() and not line.startswith('#') and '=' in line:
            key, value = line.split('=', 1)
            os.environ[key.strip()] = value.strip()

# User ID для проверки
user_id = input("Enter user ID (или нажми Enter для 229838448): ").strip()
if not user_id:
    user_id = "229838448"

session_id = f"user_{user_id}"
url = f"https://ignatova-stroinost-bot-production.up.railway.app/debug/memory/{session_id}"

print(f"\n🔍 Проверяем Zep память для session: {session_id}\n")
print("=" * 80)

response = requests.get(url)
data = response.json()

if data.get('status') == 'success':
    print(f"✅ Статус: {data['status']}")
    print(f"📊 Количество сообщений: {data['messages_count']}")
    print(f"📏 Длина контекста: {data['context_length']} символов")
    print("\n" + "=" * 80)
    print("📝 ПОСЛЕДНИЕ СООБЩЕНИЯ:")
    print("=" * 80 + "\n")
    
    for i, msg in enumerate(data.get('recent_messages', []), 1):
        role = msg['role']
        content = msg['content']
        
        # Обрезаем длинные сообщения
        if len(content) > 200:
            content = content[:200] + "..."
        
        print(f"{i}. [{role}]: {content}\n")
    
    print("=" * 80)
    print("🧠 ZEP CONTEXT PREVIEW:")
    print("=" * 80)
    
    context_preview = data.get('context_preview', '')
    if len(context_preview) > 500:
        print(context_preview[:500] + "...")
    else:
        print(context_preview)
    
    print("\n" + "=" * 80)
    print(f"💡 Полный context доступен через API")
    print(f"   Endpoint: GET /debug/memory/{session_id}")
    print("=" * 80)
    
else:
    print(f"❌ Ошибка: {data.get('error', 'Unknown error')}")
    print(json.dumps(data, indent=2, ensure_ascii=False))

