#!/usr/bin/env python3
"""
Streamlit админ панель для управления инструкциями Telegram бота
Доступ через SSH туннель: ssh -L 8502:localhost:8501 coder@104.248.39.106
"""

import os
import sys
import subprocess

def main():
    project_root = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_root)
    
    admin_script = os.path.join("admin", "streamlit_admin.py")
    
    if not os.path.exists(admin_script):
        print("❌ Файл админ панели не найден!")
        sys.exit(1)
    
    print("🚀 Textil PRO Bot - Админ панель")
    print("📝 Управление инструкциями бота")
    print("🌐 Сервер: http://localhost:8501")
    print("🔗 SSH туннель: ssh -L 8502:localhost:8501 coder@104.248.39.106")
    print("🖥️  Браузер: http://localhost:8502")
    print("🔐 Пароль: password")
    print("-" * 60)
    
    try:
        subprocess.run([
            "streamlit", "run", admin_script,
            "--server.port=8501",
            "--server.headless=true", 
            "--browser.gatherUsageStats=false"
        ], check=True)
    except KeyboardInterrupt:
        print("\n👋 Админ панель остановлена")
    except FileNotFoundError:
        print("❌ Streamlit не установлен! Запустите: pip install streamlit streamlit-ace gitpython")
        sys.exit(1)

if __name__ == "__main__":
    main()