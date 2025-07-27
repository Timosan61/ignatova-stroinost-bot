#!/usr/bin/env python3
"""
Скрипт для деплоя Streamlit админ панели на Railway
"""

import requests
import json

# Конфигурация Railway
RAILWAY_TOKEN = "d68be741-981e-4382-bce5-32281d730f25"
PROJECT_ID = "6a08cc81-8944-4807-ab6f-79b06a7840df"
ENVIRONMENT_ID = "052878b4-6d0f-4066-ad0a-d595ec530f23"
STREAMLIT_SERVICE_ID = "6342a7c0-6e2f-4fd4-ae65-972f3b83ffd8"

def railway_request(query, variables=None):
    """Выполнить GraphQL запрос к Railway API"""
    headers = {
        "Authorization": f"Bearer {RAILWAY_TOKEN}",
        "Content-Type": "application/json"
    }
    
    payload = {"query": query}
    if variables:
        payload["variables"] = variables
    
    response = requests.post(
        "https://backboard.railway.com/graphql/v2",
        headers=headers,
        json=payload
    )
    
    return response.json()

def deploy_streamlit():
    """Настроить и задеплоить Streamlit сервис"""
    
    print("🚀 Деплой Streamlit админ панели на Railway...")
    
    # 1. Попробуем принудительно запустить деплой
    deploy_query = """
    mutation {
        serviceInstanceDeploy(serviceId: "%s") {
            id
        }
    }
    """ % STREAMLIT_SERVICE_ID
    
    result = railway_request(deploy_query)
    
    if "errors" in result:
        print(f"❌ Ошибка деплоя: {result['errors']}")
        
        # Попробуем настроить переменные окружения
        print("🔧 Настройка переменных окружения...")
        
        env_vars = {
            "RAILWAY_API_KEY": RAILWAY_TOKEN,
            "STREAMLIT_SERVER_ADDRESS": "0.0.0.0"
        }
        
        for key, value in env_vars.items():
            var_query = """
            mutation {
                variableUpsert(input: {
                    environmentId: "%s"
                    serviceId: "%s"
                    name: "%s"
                    value: "%s"
                }) {
                    id
                }
            }
            """ % (ENVIRONMENT_ID, STREAMLIT_SERVICE_ID, key, value)
            
            var_result = railway_request(var_query)
            if "errors" not in var_result:
                print(f"✅ Переменная {key} настроена")
            else:
                print(f"❌ Ошибка настройки {key}: {var_result['errors']}")
    else:
        print("✅ Деплой запущен успешно!")
    
    # 2. Получить URL сервиса
    service_query = """
    query {
        service(id: "%s") {
            domains {
                domain
            }
        }
    }
    """ % STREAMLIT_SERVICE_ID
    
    service_result = railway_request(service_query)
    
    if "errors" not in service_result and service_result.get("data", {}).get("service", {}).get("domains"):
        domains = service_result["data"]["service"]["domains"]
        if domains:
            print(f"🌐 Streamlit будет доступен по адресу: https://{domains[0]['domain']}")
        else:
            print("🔧 Домен будет назначен автоматически после деплоя")
    
    print("\n📋 Инструкции:")
    print("1. Дождитесь завершения деплоя (2-3 минуты)")
    print("2. Откройте Railway Dashboard: https://railway.app/dashboard")
    print("3. Найдите сервис 'admin-panel' в проекте 'textil-pro-bot'")
    print("4. Скопируйте публичный URL из настроек сервиса")
    print("5. Пароль для входа: password")

if __name__ == "__main__":
    deploy_streamlit()