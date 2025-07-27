#!/usr/bin/env python3
"""
Railway deployment monitoring script
"""

import sys
import os
import time
import json
from datetime import datetime
sys.path.insert(0, '/home/coder/.local/lib/python3.12/site-packages')

import requests
from typing import Dict, Any, Optional

class RailwayMonitor:
    def __init__(self, api_token: str):
        self.api_token = api_token
        self.base_url = "https://backboard.railway.com/graphql/v2"
        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
            "User-Agent": "Railway-Monitor-Script/1.0"
        }
    
    def _make_request(self, query: str, variables: Dict[str, Any] = None) -> Dict[str, Any]:
        """Make GraphQL request to Railway API"""
        payload = {
            "query": query,
            "variables": variables or {}
        }
        
        response = requests.post(
            self.base_url,
            headers=self.headers,
            json=payload
        )
        
        if response.status_code != 200:
            raise Exception(f"API request failed: {response.status_code} - {response.text}")
        
        result = response.json()
        if "errors" in result:
            raise Exception(f"GraphQL errors: {result['errors']}")
        
        return result["data"]
    
    def get_deployment_status(self, deployment_id: str) -> Dict[str, Any]:
        """Get deployment status by ID"""
        query = """
        query deployment($id: String!) {
            deployment(id: $id) {
                id
                status
                createdAt
                updatedAt
                url
                staticUrl
                service {
                    id
                    name
                }
                environment {
                    id
                    name
                }
            }
        }
        """
        variables = {"id": deployment_id}
        
        result = self._make_request(query, variables)
        return result.get("deployment")
    
    def get_deployment_logs(self, deployment_id: str, limit: int = 100) -> list:
        """Get deployment logs"""
        query = """
        query deploymentLogs($deploymentId: String!, $limit: Int) {
            deploymentLogs(deploymentId: $deploymentId, limit: $limit) {
                edges {
                    node {
                        id
                        message
                        timestamp
                        severity
                    }
                }
            }
        }
        """
        variables = {"deploymentId": deployment_id, "limit": limit}
        
        try:
            result = self._make_request(query, variables)
            logs = result.get("deploymentLogs", {}).get("edges", [])
            return [edge["node"] for edge in logs]
        except Exception as e:
            print(f"⚠️ Не удалось получить логи: {e}")
            return []
    
    def get_service_status(self, service_id: str) -> Dict[str, Any]:
        """Get current service status"""
        query = """
        query service($id: String!) {
            service(id: $id) {
                id
                name
                serviceInstances {
                    edges {
                        node {
                            id
                            status
                            createdAt
                            updatedAt
                            domains {
                                domain
                                serviceDomain
                            }
                            latestDeployment {
                                id
                                status
                                createdAt
                            }
                        }
                    }
                }
            }
        }
        """
        variables = {"id": service_id}
        
        result = self._make_request(query, variables)
        return result.get("service")
    
    def get_project_services(self, project_id: str) -> list:
        """Get all services in a project"""
        query = """
        query project($id: String!) {
            project(id: $id) {
                id
                name
                services {
                    edges {
                        node {
                            id
                            name
                        }
                    }
                }
            }
        }
        """
        variables = {"id": project_id}
        
        result = self._make_request(query, variables)
        project = result.get("project")
        if not project:
            return []
        
        services = []
        for edge in project["services"]["edges"]:
            services.append(edge["node"])
        
        return services
    
    def monitor_deployment(self, deployment_id: str, timeout: int = 600):
        """Monitor deployment progress with real-time updates"""
        print(f"🚀 Мониторинг деплоя: {deployment_id}")
        print("=" * 60)
        
        start_time = time.time()
        last_log_count = 0
        
        while time.time() - start_time < timeout:
            try:
                # Получаем статус деплоя
                deployment = self.get_deployment_status(deployment_id)
                if not deployment:
                    print("❌ Деплой не найден")
                    return False
                
                status = deployment["status"]
                service_name = deployment["service"]["name"]
                env_name = deployment["environment"]["name"]
                
                print(f"📊 Статус: {status} | Сервис: {service_name} | Среда: {env_name}")
                
                # Получаем новые логи
                logs = self.get_deployment_logs(deployment_id, limit=50)
                if logs and len(logs) > last_log_count:
                    new_logs = logs[last_log_count:]
                    for log in new_logs:
                        timestamp = datetime.fromisoformat(log["timestamp"].replace('Z', '+00:00'))
                        severity = log["severity"]
                        message = log["message"].strip()
                        
                        emoji = "📝"
                        if severity == "ERROR":
                            emoji = "❌"
                        elif severity == "WARN":
                            emoji = "⚠️"
                        elif "success" in message.lower() or "completed" in message.lower():
                            emoji = "✅"
                        
                        print(f"{emoji} [{timestamp.strftime('%H:%M:%S')}] {message}")
                    
                    last_log_count = len(logs)
                
                # Проверяем завершение деплоя
                if status == "SUCCESS":
                    print("\n🎉 Деплой успешно завершен!")
                    if deployment.get("url"):
                        print(f"🔗 URL: {deployment['url']}")
                    return True
                elif status == "FAILED":
                    print("\n❌ Деплой завершился с ошибкой!")
                    return False
                elif status in ["BUILDING", "DEPLOYING"]:
                    print("⏳ Деплой в процессе...")
                else:
                    print(f"🔄 Статус: {status}")
                
                time.sleep(10)  # Ждем 10 секунд перед следующей проверкой
                
            except Exception as e:
                print(f"❌ Ошибка мониторинга: {e}")
                time.sleep(5)
        
        print(f"\n⏰ Таймаут мониторинга ({timeout} сек)")
        return False
    
    def show_project_status(self, project_id: str):
        """Show current status of all services in project"""
        print(f"📋 Статус проекта: {project_id}")
        print("=" * 60)
        
        try:
            services = self.get_project_services(project_id)
            
            if not services:
                print("❌ Проект не найден или нет доступа")
                return
            
            for service in services:
                service_name = service["name"]
                service_id = service["id"]
                
                print(f"\n🔧 Сервис: {service_name} (ID: {service_id})")
                
                # Получаем детальную информацию о сервисе
                try:
                    service_details = self.get_service_status(service_id)
                    if service_details and "serviceInstances" in service_details:
                        instances = service_details["serviceInstances"]["edges"]
                        if not instances:
                            print("  📭 Нет активных экземпляров")
                            continue
                        
                        for instance_edge in instances:
                            instance = instance_edge["node"]
                            instance_status = instance.get("status", "UNKNOWN")
                            
                            print(f"  🔄 Статус экземпляра: {instance_status}")
                            
                            if "domains" in instance:
                                domains = instance["domains"]
                                for domain in domains:
                                    if "domain" in domain:
                                        print(f"  🌐 Домен: https://{domain['domain']}")
                            
                            latest_deployment = instance.get("latestDeployment")
                            if latest_deployment:
                                deploy_status = latest_deployment["status"]
                                deploy_time = latest_deployment["createdAt"]
                                deploy_id = latest_deployment["id"]
                                
                                deploy_time_formatted = datetime.fromisoformat(
                                    deploy_time.replace('Z', '+00:00')
                                ).strftime('%Y-%m-%d %H:%M:%S')
                                
                                status_emoji = "✅" if deploy_status == "SUCCESS" else "❌" if deploy_status == "FAILED" else "🔄"
                                
                                print(f"  {status_emoji} Последний деплой: {deploy_status}")
                                print(f"  📅 Время: {deploy_time_formatted}")
                                print(f"  🆔 ID: {deploy_id}")
                            else:
                                print("  📭 Нет информации о деплоях")
                    else:
                        print("  ⚠️ Не удалось получить детали сервиса")
                        
                except Exception as e:
                    print(f"  ❌ Ошибка получения деталей сервиса: {e}")
                        
        except Exception as e:
            print(f"❌ Ошибка получения статуса: {e}")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Monitor Railway deployments")
    parser.add_argument("--project-id", help="Project ID to monitor")
    parser.add_argument("--deployment-id", help="Specific deployment ID to monitor")
    parser.add_argument("--service-id", help="Service ID to check status")
    parser.add_argument("--timeout", type=int, default=600, help="Monitoring timeout in seconds")
    
    args = parser.parse_args()
    
    # Get Railway token
    api_token = os.getenv("RAILWAY_TOKEN")
    if not api_token:
        print("❌ RAILWAY_TOKEN environment variable is required")
        sys.exit(1)
    
    monitor = RailwayMonitor(api_token)
    
    try:
        if args.deployment_id:
            # Monitor specific deployment
            success = monitor.monitor_deployment(args.deployment_id, args.timeout)
            sys.exit(0 if success else 1)
        elif args.project_id:
            # Show project status
            monitor.show_project_status(args.project_id)
        elif args.service_id:
            # Show service status
            service = monitor.get_service_status(args.service_id)
            print(json.dumps(service, indent=2, ensure_ascii=False))
        else:
            # Default: show status of known project
            project_id = "6a08cc81-8944-4807-ab6f-79b06a7840df"
            monitor.show_project_status(project_id)
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()