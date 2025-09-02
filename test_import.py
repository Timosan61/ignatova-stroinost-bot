#!/usr/bin/env python3
"""
Тест импорта модулей для диагностики проблем на Railway
"""

import sys
import traceback
print(f"Python version: {sys.version}")

print("🔄 Тестируем импорт модулей...")

# Тест 1: Базовые модули
try:
    import json
    import asyncio
    import logging
    from datetime import datetime
    from typing import Optional, Dict, Any
    print("✅ Базовые модули импортированы")
except Exception as e:
    print(f"❌ Ошибка базовых модулей: {e}")

# Тест 2: OpenAI
try:
    import openai
    print("✅ OpenAI импортирован")
except Exception as e:
    print(f"❌ Ошибка OpenAI: {e}")

# Тест 3: Anthropic
try:
    import anthropic
    print("✅ Anthropic импортирован")
except Exception as e:
    print(f"❌ Ошибка Anthropic: {e}")

# Тест 4: Zep Cloud
try:
    from zep_cloud.client import AsyncZep
    from zep_cloud.types import Message
    print("✅ Zep Cloud импортирован")
except Exception as e:
    print(f"❌ Ошибка Zep Cloud: {e}")
    traceback.print_exc()

# Тест 5: Конфиг бота
try:
    from bot.config import (
        INSTRUCTION_FILE, OPENAI_API_KEY, ANTHROPIC_API_KEY, 
        ZEP_API_KEY, VOICE_ENABLED, TELEGRAM_BOT_TOKEN
    )
    print("✅ Bot config импортирован")
except Exception as e:
    print(f"❌ Ошибка Bot config: {e}")
    traceback.print_exc()

# Тест 6: VoiceService
try:
    from bot.voice.voice_service import VoiceService
    print("✅ VoiceService импортирован")
except Exception as e:
    print(f"❌ Ошибка VoiceService: {e}")
    traceback.print_exc()

# Тест 7: TextilProAgent
try:
    from bot.agent import TextilProAgent
    print("✅ TextilProAgent импортирован успешно")
    
    # Попытка создать экземпляр
    agent = TextilProAgent()
    print("✅ TextilProAgent инициализирован успешно")
    
except Exception as e:
    print(f"❌ Ошибка TextilProAgent: {e}")
    traceback.print_exc()

print("🎉 Тест импорта завершен")