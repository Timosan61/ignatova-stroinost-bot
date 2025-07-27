import streamlit as st
import git
import os
import requests
import base64
import json
from datetime import datetime
from typing import Optional, Dict, Any

class DeployManager:
    def __init__(self):
        self.repo_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # GitHub API настройки
        self.github_token = st.secrets.get("GITHUB_TOKEN", os.getenv("GITHUB_TOKEN"))
        self.github_owner = st.secrets.get("GITHUB_OWNER", "Timosan61")
        self.github_repo = st.secrets.get("GITHUB_REPO", "Textill_PRO_BOT")
        self.github_api_base = "https://api.github.com"
        
        # Railway настройки
        self.railway_token = st.secrets.get("RAILWAY_TOKEN", os.getenv("RAILWAY_TOKEN"))
        self.railway_project_id = st.secrets.get("RAILWAY_PROJECT_ID", os.getenv("RAILWAY_PROJECT_ID"))
        self.railway_service_id = st.secrets.get("RAILWAY_SERVICE_ID", os.getenv("RAILWAY_SERVICE_ID"))
        
    def get_git_status(self) -> Dict[str, Any]:
        """Получает статус Git репозитория"""
        try:
            repo = git.Repo(self.repo_path)
            
            # Проверяем, есть ли uncommitted изменения
            is_dirty = repo.is_dirty()
            untracked_files = repo.untracked_files
            
            # Получаем последний коммит
            last_commit = repo.head.commit
            
            return {
                "is_dirty": is_dirty,
                "untracked_files": untracked_files,
                "last_commit_sha": last_commit.hexsha[:8],
                "last_commit_message": last_commit.message.strip(),
                "last_commit_date": datetime.fromtimestamp(last_commit.committed_date),
                "current_branch": repo.active_branch.name,
                "status": "clean" if not is_dirty and not untracked_files else "dirty"
            }
        except Exception as e:
            return {"error": str(e)}
    
    def get_file_content_from_github(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Получает содержимое файла из GitHub через API"""
        try:
            url = f"{self.github_api_base}/repos/{self.github_owner}/{self.github_repo}/contents/{file_path}"
            headers = {
                "Authorization": f"token {self.github_token}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                return None  # Файл не найден
            else:
                st.error(f"Ошибка получения файла: {response.status_code}")
                return None
                
        except Exception as e:
            st.error(f"Ошибка при обращении к GitHub API: {e}")
            return None
    
    def update_file_via_github_api(self, file_path: str, content: str, commit_message: str) -> bool:
        """Обновляет файл в GitHub через API"""
        try:
            # Получаем текущий файл для SHA
            current_file = self.get_file_content_from_github(file_path)
            
            url = f"{self.github_api_base}/repos/{self.github_owner}/{self.github_repo}/contents/{file_path}"
            headers = {
                "Authorization": f"token {self.github_token}",
                "Accept": "application/vnd.github.v3+json",
                "Content-Type": "application/json"
            }
            
            # Кодируем содержимое в base64
            content_encoded = base64.b64encode(content.encode('utf-8')).decode('utf-8')
            
            data = {
                "message": commit_message,
                "content": content_encoded,
                "branch": "main"
            }
            
            # Если файл существует, добавляем SHA
            if current_file:
                data["sha"] = current_file["sha"]
            
            response = requests.put(url, headers=headers, json=data)
            
            if response.status_code in [200, 201]:
                return True
            else:
                return False
                
        except Exception as e:
            return False
    
    def trigger_railway_deploy(self) -> bool:
        """Запускает деплой на Railway через API"""
        try:
            headers = {
                "Authorization": f"Bearer {self.railway_token}",
                "Content-Type": "application/json"
            }
            
            # GraphQL запрос для редеплоя службы
            query = """
            mutation serviceInstanceRedeploy($serviceId: String!) {
                serviceInstanceRedeploy(serviceId: $serviceId) {
                    id
                    status
                }
            }
            """
            
            variables = {
                "serviceId": self.railway_service_id
            }
            
            response = requests.post(
                "https://backboard.railway.com/graphql/v2",
                headers=headers,
                json={
                    "query": query,
                    "variables": variables
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                if "errors" not in result:
                    return True
                else:
                    print(f"Railway API errors: {result['errors']}")
                    return False
            else:
                print(f"Railway API request failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"Railway deploy error: {e}")
            return False
    
    def auto_deploy_changes(self, commit_message: str, instruction_content: str = None) -> bool:
        """Автоматический деплой через GitHub API + автоматическая синхронизация Railway"""
        
        if instruction_content is None:
            st.error("❌ Содержимое инструкций не предоставлено")
            return False
        
        # Проверяем наличие GitHub токена
        if not self.github_token:
            st.error("❌ GitHub токен не настроен")
            return False
        
        # Шаг 1: Обновляем файл в GitHub
        st.info("🔄 Обновление файла в GitHub...")
        github_success = self.update_file_via_github_api("data/instruction.json", instruction_content, commit_message)
        
        if not github_success:
            st.error("❌ Ошибка обновления файла в GitHub")
            return False
            
        st.success("✅ Файл обновлен в GitHub")
        
        # Информируем о автоматической синхронизации Railway
        st.info("🔄 Railway автоматически синхронизируется с GitHub...")
        st.info("⏳ Изменения будут применены через 2-3 минуты автоматически")
        st.info("💡 Используйте кнопку 'Перезагрузить промпт' ниже для ручного обновления")
        
        return True

def show_deploy_status():
    """Показывает статус деплоя в боковой панели"""
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🚀 Статус деплоя")
    
    deploy_manager = DeployManager()
    
    # Показываем информацию о GitHub API
    try:
        st.sidebar.info(f"""
        **GitHub Репозиторий:**
        {deploy_manager.github_owner}/{deploy_manager.github_repo}
        
        **GitHub API:**
        {'✅ Готов к работе' if deploy_manager.github_token else '❌ Токен не настроен'}
        
        **Railway:**
        ✅ Автосинхронизация с GitHub
        """)
    except Exception as e:
        st.sidebar.error(f"❌ Ошибка API: {e}")
    
    # Проверяем статус бота
    st.sidebar.markdown("### 🤖 Статус бота")
    try:
        import requests
        response = requests.get("https://artyom-integrator-production.up.railway.app/", timeout=5)
        if response.status_code == 200:
            st.sidebar.success("✅ Бот онлайн")
            
            # Проверяем промпт
            prompt_response = requests.get("https://artyom-integrator-production.up.railway.app/debug/prompt", timeout=5)
            if prompt_response.status_code == 200:
                prompt_data = prompt_response.json()
                st.sidebar.info(f"""
                **Промпт:**
                Обновлен: {prompt_data.get('last_updated', 'неизвестно')[:16]}
                Длина: {prompt_data.get('system_instruction_length', 0)} символов
                """)
        else:
            st.sidebar.error("❌ Бот недоступен")
    except Exception as e:
        st.sidebar.error(f"❌ Ошибка проверки бота: {str(e)[:50]}")
    
    # Пытаемся получить Git статус (может не работать в облаке)
    try:
        git_status = deploy_manager.get_git_status()
        
        if "error" not in git_status:
            # Показываем статус Git
            if git_status["status"] == "clean":
                st.sidebar.success("✅ Git: все изменения сохранены")
            else:
                st.sidebar.warning("⚠️ Git: есть несохраненные изменения")
            
            # Информация о последнем коммите
            st.sidebar.info(f"""
            **Последний коммит:**
            `{git_status['last_commit_sha']}`
            
            **Сообщение:**
            {git_status['last_commit_message'][:50]}...
            
            **Дата:**
            {git_status['last_commit_date'].strftime('%d.%m.%Y %H:%M')}
            """)
        else:
            st.sidebar.warning("⚠️ Локальный Git недоступен (работает через GitHub API)")
    except Exception:
        st.sidebar.warning("⚠️ Локальный Git недоступен (работает через GitHub API)")
    
    return deploy_manager