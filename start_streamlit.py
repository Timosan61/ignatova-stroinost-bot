#!/usr/bin/env python3
"""
Streamlit приложение для администрирования бота
Запуск полнофункциональной админки с авторизацией
"""

import sys
import os
from pathlib import Path

# Добавляем текущую директорию в путь Python
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Импортируем главную админку
from admin.streamlit_admin import main

if __name__ == "__main__":
    main()