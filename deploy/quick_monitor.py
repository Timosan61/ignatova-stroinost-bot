#!/usr/bin/env python3
"""
Простой мониторинг Railway деплоя через CLI команды
"""

import subprocess
import sys
import os
import time

def run_railway_command(command):
    """Запуск Railway CLI команды"""
    try:
        result = subprocess.run(
            f"railway {command}",
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired:
        return "", "Timeout", 1
    except Exception as e:
        return "", str(e), 1

def check_railway_cli():
    """Проверка установки Railway CLI"""
    stdout, stderr, code = run_railway_command("--version")
    if code == 0:
        print(f"✅ Railway CLI найден: {stdout.strip()}")
        return True
    else:
        print("❌ Railway CLI не найден")
        print("📥 Установите: npm install -g @railway/cli")
        print("🔗 Документация: https://docs.railway.app/develop/cli")
        return False

def login_railway():
    """Вход в Railway CLI"""
    print("🔐 Попытка входа в Railway...")
    stdout, stderr, code = run_railway_command("login")
    if code == 0:
        print("✅ Успешный вход в Railway")
        return True
    else:
        print("❌ Ошибка входа в Railway")
        print(f"Ошибка: {stderr}")
        return False

def get_project_status():
    """Получение статуса проекта"""
    print("📋 Получение статуса проекта...")
    stdout, stderr, code = run_railway_command("status")
    if code == 0:
        print("✅ Статус проекта:")
        print(stdout)
        return True
    else:
        print("❌ Ошибка получения статуса")
        print(f"Ошибка: {stderr}")
        return False

def get_deployment_logs(service_name=None):
    """Получение логов деплоя"""
    cmd = "logs"
    if service_name:
        cmd += f" --service {service_name}"
    
    print(f"📜 Получение логов{' сервиса ' + service_name if service_name else ''}...")
    stdout, stderr, code = run_railway_command(cmd)
    if code == 0:
        print("📋 Логи:")
        print(stdout)
        return True
    else:
        print("❌ Ошибка получения логов")
        print(f"Ошибка: {stderr}")
        return False

def monitor_with_cli():
    """Мониторинг через Railway CLI"""
    print("🚀 Мониторинг Railway проекта через CLI")
    print("=" * 60)
    
    if not check_railway_cli():
        return False
    
    # Попытка получить статус без логина (если уже залогинен)
    if get_project_status():
        print("\n" + "="*40)
        get_deployment_logs("bot")
        print("\n" + "="*40)
        get_deployment_logs("admin-panel")
        return True
    else:
        print("🔐 Требуется авторизация...")
        if login_railway():
            return monitor_with_cli()
        else:
            return False

def show_manual_commands():
    """Показать ручные команды для мониторинга"""
    print("""
🛠️ Ручные команды для мониторинга Railway:

1. Установка Railway CLI:
   npm install -g @railway/cli

2. Вход в аккаунт:
   railway login

3. Подключение к проекту:
   railway link <project-id>
   
4. Просмотр статуса:
   railway status

5. Просмотр логов:
   railway logs
   railway logs --service bot
   railway logs --service admin-panel

6. Мониторинг в реальном времени:
   railway logs --follow

7. Информация о сервисах:
   railway service list

🌐 Веб-интерфейс: https://railway.app/project/6a08cc81-8944-4807-ab6f-79b06a7840df
""")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Quick Railway monitoring")
    parser.add_argument("--manual", action="store_true", help="Show manual commands")
    parser.add_argument("--logs", help="Get logs for specific service")
    
    args = parser.parse_args()
    
    if args.manual:
        show_manual_commands()
    elif args.logs:
        get_deployment_logs(args.logs)
    else:
        success = monitor_with_cli()
        if not success:
            print("\n💡 Используйте --manual для просмотра ручных команд")
            show_manual_commands()

if __name__ == "__main__":
    main()