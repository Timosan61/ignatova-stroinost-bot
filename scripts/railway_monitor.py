#!/usr/bin/env python3
"""
Railway Deployment Monitor
Использует GraphQL API для мониторинга deployments и получения логов
"""

import os
import sys
import json
import time
import requests
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List

# Загрузка переменных из .env
env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value

# Конфигурация
RAILWAY_TOKEN = os.getenv('RAILWAY_TOKEN')
API_URL = 'https://backboard.railway.app/graphql/v2'
PROJECT_ID = 'a470438c-3a6c-4952-80df-9e2c067233c6'
SERVICE_ID = '3eb7a84e-5693-457b-8fe1-2f4253713a0c'

# Цвета для терминала
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    CYAN = '\033[0;36m'
    NC = '\033[0m'  # No Color

def railway_query(query: str) -> Dict:
    """Выполнить GraphQL запрос к Railway API"""
    if not RAILWAY_TOKEN:
        print(f"{Colors.RED}❌ RAILWAY_TOKEN не найден в .env{Colors.NC}")
        sys.exit(1)

    headers = {
        'Authorization': f'Bearer {RAILWAY_TOKEN}',
        'Content-Type': 'application/json',
    }

    response = requests.post(
        API_URL,
        json={'query': query},
        headers=headers,
        timeout=30
    )

    if response.status_code != 200:
        print(f"{Colors.RED}❌ HTTP {response.status_code}: {response.text}{Colors.NC}")
        sys.exit(1)

    data = response.json()

    if 'errors' in data:
        print(f"{Colors.RED}❌ GraphQL errors:{Colors.NC}")
        for error in data['errors']:
            print(f"  {error.get('message', 'Unknown error')}")
        sys.exit(1)

    return data.get('data', {})

def list_deployments(limit: int = 10) -> List[Dict]:
    """Получить список последних deployments"""
    query = f"""
    query {{
        deployments(
            input: {{
                projectId: "{PROJECT_ID}",
                serviceId: "{SERVICE_ID}"
            }},
            first: {limit}
        ) {{
            edges {{
                node {{
                    id
                    status
                    staticUrl
                    createdAt
                    updatedAt
                }}
            }}
        }}
    }}
    """

    data = railway_query(query)
    deployments = []

    for edge in data.get('deployments', {}).get('edges', []):
        node = edge['node']
        deployments.append(node)

    return deployments

def get_deployment_info(deployment_id: str) -> Optional[Dict]:
    """Получить информацию о deployment"""
    query = f"""
    query {{
        deployment(id: "{deployment_id}") {{
            id
            status
            staticUrl
            createdAt
            updatedAt
        }}
    }}
    """

    data = railway_query(query)
    return data.get('deployment')

def get_service_vars() -> Dict[str, str]:
    """Получить переменные окружения сервиса"""
    # Сначала получаем environmentId
    query = f"""
    query {{
        service(id: "{SERVICE_ID}") {{
            name
            serviceInstances {{
                edges {{
                    node {{
                        environmentId
                        latestDeployment {{
                            id
                            status
                        }}
                    }}
                }}
            }}
        }}
    }}
    """

    data = railway_query(query)
    service = data.get('service', {})

    # Получаем первый environment ID
    instances = service.get('serviceInstances', {}).get('edges', [])
    if not instances:
        return {}

    environment_id = instances[0]['node']['environmentId']

    # Запрашиваем переменные для этого environment
    vars_query = f"""
    query {{
        variables(
            environmentId: "{environment_id}",
            serviceId: "{SERVICE_ID}"
        ) {{
            edges {{
                node {{
                    name
                    value
                }}
            }}
        }}
    }}
    """

    vars_data = railway_query(vars_query)
    variables = {}

    for edge in vars_data.get('variables', {}).get('edges', []):
        node = edge['node']
        variables[node['name']] = node['value']

    return variables

def format_status(status: str) -> str:
    """Форматировать статус с цветом"""
    colors = {
        'SUCCESS': Colors.GREEN,
        'FAILED': Colors.RED,
        'WAITING': Colors.YELLOW,
        'BUILDING': Colors.CYAN,
        'SKIPPED': Colors.NC,
    }
    color = colors.get(status, Colors.NC)
    return f"{color}{status}{Colors.NC}"

def format_datetime(dt_str: str) -> str:
    """Форматировать datetime"""
    try:
        dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        return dt.strftime('%Y-%m-%d %H:%M:%S UTC')
    except:
        return dt_str

def print_deployments(deployments: List[Dict]):
    """Вывести список deployments"""
    print(f"\n{Colors.BLUE}📦 Последние deployments:{Colors.NC}\n")

    for dep in deployments:
        created = format_datetime(dep['createdAt'])
        status = format_status(dep['status'])

        print(f"{created} | {status}")
        print(f"  ID: {dep['id']}")
        print(f"  URL: {dep['staticUrl']}")
        print()

def print_deployment_info(deployment: Dict):
    """Вывести информацию о deployment"""
    print(f"\n{Colors.BLUE}📦 Deployment Info:{Colors.NC}\n")
    print(f"ID: {deployment['id']}")
    print(f"Status: {format_status(deployment['status'])}")
    print(f"URL: {deployment['staticUrl']}")
    print(f"Created: {format_datetime(deployment['createdAt'])}")
    print(f"Updated: {format_datetime(deployment['updatedAt'])}")

def monitor_deployments(interval: int = 10):
    """Мониторинг deployments в реальном времени"""
    print(f"{Colors.GREEN}🔍 Мониторинг deployments{Colors.NC}")
    print(f"{Colors.YELLOW}(Обновление каждые {interval}с, Ctrl+C для выхода){Colors.NC}\n")

    try:
        while True:
            os.system('clear' if os.name == 'posix' else 'cls')
            deployments = list_deployments(5)
            print_deployments(deployments)
            time.sleep(interval)
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}👋 Мониторинг остановлен{Colors.NC}")

def main():
    """Главная функция"""
    import argparse

    parser = argparse.ArgumentParser(description='Railway Deployment Monitor')
    parser.add_argument('command', choices=['list', 'info', 'monitor', 'vars'],
                        help='Команда для выполнения')
    parser.add_argument('--id', help='ID deployment (для команды info)')
    parser.add_argument('--limit', type=int, default=10,
                        help='Количество deployments (для команды list)')
    parser.add_argument('--interval', type=int, default=10,
                        help='Интервал обновления в секундах (для команды monitor)')

    args = parser.parse_args()

    if args.command == 'list':
        deployments = list_deployments(args.limit)
        print_deployments(deployments)

    elif args.command == 'info':
        if not args.id:
            # Получить последний deployment
            deployments = list_deployments(1)
            if deployments:
                args.id = deployments[0]['id']
            else:
                print(f"{Colors.RED}❌ Не найдено ни одного deployment{Colors.NC}")
                sys.exit(1)

        deployment = get_deployment_info(args.id)
        if deployment:
            print_deployment_info(deployment)
        else:
            print(f"{Colors.RED}❌ Deployment {args.id} не найден{Colors.NC}")

    elif args.command == 'monitor':
        monitor_deployments(args.interval)

    elif args.command == 'vars':
        print(f"\n{Colors.BLUE}🔧 Service Info:{Colors.NC}\n")
        service = get_service_vars()
        print(json.dumps(service, indent=2))

if __name__ == '__main__':
    main()
