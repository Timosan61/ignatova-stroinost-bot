#!/usr/bin/env python3
"""
Deploy to existing Railway project script
"""

import sys
import os
sys.path.insert(0, '/home/coder/.local/lib/python3.12/site-packages')

import requests
import json
from typing import Dict, Any, Optional

class RailwayUpdater:
    def __init__(self, api_token: str):
        self.api_token = api_token
        self.base_url = "https://backboard.railway.com/graphql/v2"
        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
            "User-Agent": "Railway-Update-Script/1.0"
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
        services = []
        
        if result["project"] and result["project"]["services"]:
            for edge in result["project"]["services"]["edges"]:
                services.append({
                    "id": edge["node"]["id"],
                    "name": edge["node"]["name"]
                })
        
        return services
    
    def set_environment_variables(self, service_id: str, env_vars: Dict[str, str]):
        """Set environment variables for a service"""
        for key, value in env_vars.items():
            query = """
            mutation variableUpsert($input: VariableUpsertInput!) {
                variableUpsert(input: $input) {
                    id
                    name
                }
            }
            """
            variables = {
                "input": {
                    "serviceId": service_id,
                    "name": key,
                    "value": value
                }
            }
            
            try:
                self._make_request(query, variables)
                print(f"✅ Environment variable set: {key}")
            except Exception as e:
                print(f"❌ Failed to set {key}: {e}")
    
    def redeploy_service(self, service_id: str) -> str:
        """Redeploy a service"""
        query = """
        mutation serviceInstanceRedeploy($serviceId: String!) {
            serviceInstanceRedeploy(serviceId: $serviceId) {
                id
                status
            }
        }
        """
        variables = {"serviceId": service_id}
        
        try:
            result = self._make_request(query, variables)
            deployment_id = result["serviceInstanceRedeploy"]["id"]
            print(f"✅ Redeployment started (ID: {deployment_id})")
            return deployment_id
        except Exception as e:
            print(f"❌ Failed to redeploy: {e}")
            return None

def main():
    # Check for Railway API token
    api_token = os.getenv("RAILWAY_TOKEN")
    if not api_token:
        print("❌ RAILWAY_TOKEN environment variable is required")
        sys.exit(1)
    
    # Bot configuration
    bot_token = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        print("❌ BOT_TOKEN or TELEGRAM_BOT_TOKEN environment variable is required")
        sys.exit(1)
    
    # Existing project ID
    project_id = "6a08cc81-8944-4807-ab6f-79b06a7840df"
    
    updater = RailwayUpdater(api_token)
    
    try:
        print("🚀 Updating existing Railway project...")
        print(f"Project ID: {project_id}")
        
        # Get project services
        services = updater.get_project_services(project_id)
        print(f"Found {len(services)} services:")
        for service in services:
            print(f"  - {service['name']} (ID: {service['id']})")
        
        if not services:
            print("❌ No services found in project")
            sys.exit(1)
        
        # Use first service or find bot service
        target_service = services[0]
        for service in services:
            if "bot" in service["name"].lower() or "textill" in service["name"].lower():
                target_service = service
                break
        
        service_id = target_service["id"]
        service_name = target_service["name"]
        
        print(f"🎯 Updating service: {service_name} (ID: {service_id})")
        
        # Set environment variables
        env_vars = {
            "BOT_TOKEN": bot_token,
            "TELEGRAM_BOT_TOKEN": bot_token,
            "PYTHONPATH": "/app",
            "PORT": "8000"
        }
        
        # Add optional environment variables if they exist
        optional_vars = ["ADMIN_PASSWORD", "OPENAI_API_KEY", "DATABASE_URL", "ZEP_API_KEY", "BOT_USERNAME"]
        for var in optional_vars:
            value = os.getenv(var)
            if value:
                env_vars[var] = value
        
        updater.set_environment_variables(service_id, env_vars)
        
        # Redeploy service
        deployment_id = updater.redeploy_service(service_id)
        
        if deployment_id:
            print(f"""
🎉 Deployment update started!

Project: https://railway.app/project/{project_id}
Service: {service_name} (ID: {service_id})
Deployment ID: {deployment_id}

""")
            
            # Предлагаем мониторинг деплоя
            try:
                monitor_choice = input("🔍 Хотите отслеживать прогресс деплоя? (y/N): ").lower()
                if monitor_choice in ['y', 'yes', 'да']:
                    from .monitor_deploy import RailwayMonitor
                    monitor = RailwayMonitor(api_token)
                    print("\n" + "="*60)
                    monitor.monitor_deployment(deployment_id, timeout=600)
                else:
                    print("✅ Мониторинг деплоя можно запустить командой:")
                    print(f"python deploy/monitor_deploy.py --deployment-id {deployment_id}")
            except KeyboardInterrupt:
                print("\n⏹️ Мониторинг остановлен пользователем")
            except Exception as e:
                print(f"\n⚠️ Ошибка запуска мониторинга: {e}")
                print(f"Запустите мониторинг вручную: python deploy/monitor_deploy.py --deployment-id {deployment_id}")
        else:
            print("""
❌ Deployment failed to start!

Check the Railway dashboard for more details.
""")
    
    except Exception as e:
        print(f"❌ Update failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()