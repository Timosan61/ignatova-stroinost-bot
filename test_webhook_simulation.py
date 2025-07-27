#!/usr/bin/env python3
"""
Симуляция webhook для тестирования изменений
"""

import asyncio
import json
import sys
import os

sys.path.append('.')

async def simulate_message():
    """Симулируем обработку сообщения как в webhook"""
    
    # Симулируем структуру webhook update
    mock_update = {
        "message": {
            "message_id": 123,
            "from": {
                "id": 123456789,
                "first_name": "Тест",
                "last_name": "Пользователь",
                "username": "test_user"
            },
            "chat": {
                "id": 123456789,
                "type": "private"
            },
            "text": "Привет! Мне нужна помощь с производством футболок"
        }
    }
    
    print("🧪 СИМУЛЯЦИЯ ОБРАБОТКИ СООБЩЕНИЯ")
    print("="*50)
    
    try:
        # Пытаемся импортировать агент
        from bot.agent import agent
        print("✅ Agent загружен")
        
        # Извлекаем данные как в webhook
        msg = mock_update["message"]
        chat_id = msg["chat"]["id"]
        text = msg.get("text", "")
        user_id = msg.get("from", {}).get("id", "unknown")
        user_name = msg.get("from", {}).get("first_name", "Пользователь")
        
        print(f"📨 Сообщение от {user_name} (ID: {user_id}): {text}")
        
        # Тестируем новую логику
        session_id = f"user_{user_id}"
        print(f"🔗 Session ID: {session_id}")
        
        # Проверяем создание пользователя
        if agent.zep_client:
            print("🟢 Zep клиент доступен, создаем пользователя...")
            await agent.ensure_user_exists(f"user_{user_id}", {
                'first_name': user_name,
                'email': f'{user_id}@telegram.user'
            })
            await agent.ensure_session_exists(session_id, f"user_{user_id}")
        else:
            print("🟡 Zep клиент недоступен, используем локальную память")
        
        # Генерируем ответ
        print("🤖 Генерируем ответ...")
        response = await agent.generate_response(text, session_id, user_name)
        
        print(f"✅ Ответ сгенерирован:")
        print(f"   {response[:200]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(simulate_message())
    if success:
        print("\n✅ Симуляция прошла успешно!")
    else:
        print("\n❌ Симуляция провалилась!")
        sys.exit(1)