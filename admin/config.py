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
    'page_title': 'Textil PRO Bot Admin',
    'page_icon': '🤖',
    'layout': 'wide'
}

# Дефолтные значения для инструкций
DEFAULT_INSTRUCTION = {
    "system_instruction": "",
    "welcome_message": "",
    "last_updated": None
}