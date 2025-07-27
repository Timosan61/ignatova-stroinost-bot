#!/usr/bin/env python3
"""
Railway API deployment script for Textill PRO BOT
"""

import sys
import os
sys.path.insert(0, '/home/coder/.local/lib/python3.12/site-packages')

import requests
import json
from typing import Dict, Any, Optional

class RailwayDeployer:
    def __init__(self, api_token: str):
        self.api_token = api_token
        self.base_url = "https://backboard.railway.com/graphql/v2"
        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
            "User-Agent": "Railway-Deploy-Script/1.0"
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
    
    def create_project(self, name: str, description: str = "") -> str:
        """Create a new Railway project"""
        query = """
        mutation projectCreate($input: ProjectCreateInput!) {
            projectCreate(input: $input) {
                id
                name
            }
        }
        """
        variables = {
            "input": {
                "name": name,
                "description": description,
                "isPublic": False
            }
        }
        
        result = self._make_request(query, variables)
        project_id = result["projectCreate"]["id"]
        print(f"✅ Project created: {name} (ID: {project_id})")
        return project_id
    
    def create_service(self, project_id: str, name: str, source_repo: str = None) -> str:
        """Create a service in the project"""
        query = """
        mutation serviceCreate($input: ServiceCreateInput!) {
            serviceCreate(input: $input) {
                id
                name
            }
        }
        """
        
        variables = {
            "input": {
                "projectId": project_id,
                "name": name,
                "source": {
                    "repo": source_repo
                } if source_repo else None
            }
        }
        
        result = self._make_request(query, variables)
        service_id = result["serviceCreate"]["id"]
        print(f"✅ Service created: {name} (ID: {service_id})")
        return service_id
    
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
            
            self._make_request(query, variables)
            print(f"✅ Environment variable set: {key}")
    
    def deploy_service(self, service_id: str) -> str:
        """Deploy a service"""
        query = """
        mutation serviceInstanceDeploy($serviceId: String!) {
            serviceInstanceDeploy(serviceId: $serviceId) {
                id
                status
            }
        }
        """
        variables = {"serviceId": service_id}
        
        result = self._make_request(query, variables)
        deployment_id = result["serviceInstanceDeploy"]["id"]
        print(f"✅ Deployment started (ID: {deployment_id})")
        return deployment_id
    
    def get_service_url(self, service_id: str) -> Optional[str]:
        """Get the public URL of a service"""
        query = """
        query service($id: String!) {
            service(id: $id) {
                id
                name
                serviceInstances {
                    domains {
                        domain
                    }
                }
            }
        }
        """
        variables = {"id": service_id}
        
        result = self._make_request(query, variables)
        service = result["service"]
        
        if service["serviceInstances"]:
            domains = service["serviceInstances"][0].get("domains", [])
            if domains:
                return f"https://{domains[0]['domain']}"
        
        return None

def main():
    # Check for Railway API token
    api_token = os.getenv("RAILWAY_TOKEN")
    if not api_token:
        print("❌ RAILWAY_TOKEN environment variable is required")
        print("Get your token from: https://railway.app/account/tokens")
        sys.exit(1)
    
    # Bot configuration
    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        print("❌ BOT_TOKEN environment variable is required")
        sys.exit(1)
    
    deployer = RailwayDeployer(api_token)
    
    try:
        print("🚀 Starting Railway deployment...")
        
        # Create project
        project_id = deployer.create_project(
            name="textill-pro-bot",
            description="Textill PRO Telegram Bot"
        )
        
        # Create service
        service_id = deployer.create_service(
            project_id=project_id,
            name="bot-service"
        )
        
        # Set environment variables
        env_vars = {
            "BOT_TOKEN": bot_token,
            "PYTHONPATH": "/app",
            "PORT": "8000"
        }
        
        # Add optional environment variables if they exist
        optional_vars = ["ADMIN_PASSWORD", "OPENAI_API_KEY", "DATABASE_URL"]
        for var in optional_vars:
            value = os.getenv(var)
            if value:
                env_vars[var] = value
        
        deployer.set_environment_variables(service_id, env_vars)
        
        # Deploy service
        deployment_id = deployer.deploy_service(service_id)
        
        print(f"""
🎉 Deployment completed successfully!

Project ID: {project_id}
Service ID: {service_id}
Deployment ID: {deployment_id}

You can monitor your deployment at:
https://railway.app/project/{project_id}

Note: It may take a few minutes for the service to be fully available.
""")
        
        # Try to get service URL
        service_url = deployer.get_service_url(service_id)
        if service_url:
            print(f"Service URL: {service_url}")
    
    except Exception as e:
        print(f"❌ Deployment failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()