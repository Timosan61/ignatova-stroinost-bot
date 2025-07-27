#!/usr/bin/env python3
"""
Delete Railway project script
"""

import sys
import os
sys.path.insert(0, '/home/coder/.local/lib/python3.12/site-packages')

import requests
import json

def delete_railway_project(api_token: str, project_id: str):
    """Delete Railway project by ID"""
    
    base_url = "https://backboard.railway.com/graphql/v2"
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
        "User-Agent": "Railway-Delete-Script/1.0"
    }
    
    # GraphQL mutation to delete project
    query = """
    mutation projectDelete($id: String!) {
        projectDelete(id: $id)
    }
    """
    
    variables = {
        "id": project_id
    }
    
    payload = {
        "query": query,
        "variables": variables
    }
    
    try:
        response = requests.post(base_url, headers=headers, json=payload)
        
        if response.status_code != 200:
            print(f"❌ API request failed: {response.status_code} - {response.text}")
            return False
        
        result = response.json()
        if "errors" in result:
            print(f"❌ GraphQL errors: {result['errors']}")
            return False
        
        print(f"✅ Project {project_id} deleted successfully")
        return True
        
    except Exception as e:
        print(f"❌ Error deleting project: {e}")
        return False

def main():
    # Get Railway token
    api_token = os.getenv("RAILWAY_TOKEN")
    if not api_token:
        print("❌ RAILWAY_TOKEN environment variable is required")
        sys.exit(1)
    
    # Project ID to delete
    project_id = "48e3c574-b00f-49d3-a9d9-35e9ae2d338b"
    
    print(f"🗑️  Deleting Railway project: {project_id}")
    
    if delete_railway_project(api_token, project_id):
        print("✅ Project deleted successfully!")
    else:
        print("❌ Failed to delete project")
        sys.exit(1)

if __name__ == "__main__":
    main()