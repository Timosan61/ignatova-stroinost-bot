"""
Конфигурация для админ-панели Streamlit
Независимая от bot конфигурации и переменных окружения
"""
import os

# Базовая директория проекта
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Путь к файлу инструкций
INSTRUCTION_FILE = os.path.join(BASE_DIR, 'data', 'instruction.json')

# Настройки для Streamlit
STREAMLIT_CONFIG = {
    'page_title': 'Ignatova Stroinost Bot Admin',
    'page_icon': '🤖',
    'layout': 'wide'
}

# Дефолтные значения для инструкций
DEFAULT_INSTRUCTION = {
    "system_instruction": "Вы - помощник по строительству и ремонту от компании Игнатова Стройность.",
    "welcome_message": "Добро пожаловать! Я помощник по строительству и ремонту. Чем могу помочь?",
    "settings": {
        "voice_enabled": True,
        "memory_enabled": True,
        "debug_mode": False,
        "max_memory_messages": 50,
        "response_temperature": 0.7
    },
    "last_updated": None
}

# URL бота для проверки статуса (Railway URL)
BOT_URL = "https://ignatova-stroinost-bot-production.up.railway.app"