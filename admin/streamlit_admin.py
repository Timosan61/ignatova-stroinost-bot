import streamlit as st
import json
import os
import sys
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from admin.config import INSTRUCTION_FILE, DEFAULT_INSTRUCTION, STREAMLIT_CONFIG, BOT_URL
from admin.auth import check_password, show_auth_info


def load_instruction():
    try:
        with open(INSTRUCTION_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        default_data = DEFAULT_INSTRUCTION.copy()
        default_data["last_updated"] = datetime.now().isoformat()
        return default_data


def save_instruction(instruction_data):
    try:
        instruction_data["last_updated"] = datetime.now().isoformat()
        with open(INSTRUCTION_FILE, 'w', encoding='utf-8') as f:
            json.dump(instruction_data, f, ensure_ascii=False, indent=2)
        
        # Автоматическое обновление GitHub
        try:
            import subprocess
            import os
            
            # Переходим в корневую директорию проекта
            project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
            # Git команды для автопуша
            subprocess.run(['git', 'add', 'data/instruction.json'], 
                          cwd=project_dir, capture_output=True)
            
            commit_msg = f"Admin: Обновлены инструкции бота ({datetime.now().strftime('%H:%M')})\n\n🤖 Generated with [Claude Code](https://claude.ai/code)\n\nCo-Authored-By: Claude <noreply@anthropic.com>"
            
            subprocess.run(['git', 'commit', '-m', commit_msg], 
                          cwd=project_dir, capture_output=True)
            
            subprocess.run(['git', 'push', 'origin', 'main'], 
                          cwd=project_dir, capture_output=True)
            
            print("✅ Изменения автоматически отправлены в GitHub")
            
        except Exception as git_error:
            print(f"⚠️ Не удалось обновить GitHub: {git_error}")
            # Продолжаем работу даже если git не сработал
        
        return True
    except Exception as e:
        return False


def main():
    st.set_page_config(
        page_title=STREAMLIT_CONFIG['page_title'],
        page_icon=STREAMLIT_CONFIG['page_icon'],
        layout=STREAMLIT_CONFIG['layout']
    )
    
    # Проверка авторизации
    if not check_password():
        return
    
    # Заголовок  
    st.title("🤖 Ignatova Stroinost Bot - Админ панель")
    
    # Показываем информацию об авторизации
    show_auth_info()
    
    if not os.path.exists(INSTRUCTION_FILE):
        st.warning("⚠️ Файл инструкций не найден. Создайте новые инструкции.")
    
    instruction_data = load_instruction()
    
    # Табы для разных секций
    tab1, tab2, tab3 = st.tabs(["📝 Основные инструкции", "⚙️ Настройки", "📊 Статус бота"])
    
    with tab1:
        system_instruction = st.text_area(
            "Системная инструкция:",
            value=instruction_data.get("system_instruction", ""),
            height=500,
            help="Полная инструкция для бота - его роль, задачи и правила поведения"
        )
        
        welcome_message = st.text_area(
            "Приветственное сообщение:",
            value=instruction_data.get("welcome_message", ""),
            height=150,
            help="Сообщение которое видит пользователь при первом запуске"
        )
        
        # Информация о текущей инструкции
        st.info(f"💬 Длина системной инструкции: {len(instruction_data.get('system_instruction', ''))} символов")
    
    with tab2:
        st.subheader("⚙️ Настройки бота")
        
        settings = instruction_data.get("settings", {})
        
        col1, col2 = st.columns(2)
        
        with col1:
            voice_enabled = st.checkbox(
                "Голосовые сообщения",
                value=settings.get("voice_enabled", True),
                help="Включить обработку голосовых сообщений"
            )
            
            memory_enabled = st.checkbox(
                "Память разговоров",
                value=settings.get("memory_enabled", True),
                help="Включить сохранение контекста разговоров"
            )
        
        with col2:
            debug_mode = st.checkbox(
                "Режим отладки",
                value=settings.get("debug_mode", False),
                help="Включить расширенное логирование"
            )
            
            max_memory_messages = st.number_input(
                "Макс. сообщений в памяти",
                min_value=10,
                max_value=200,
                value=settings.get("max_memory_messages", 50),
                help="Максимальное количество сообщений для хранения"
            )
        
        response_temperature = st.slider(
            "Температура ответов",
            min_value=0.0,
            max_value=1.0,
            value=settings.get("response_temperature", 0.7),
            step=0.1,
            help="Креативность ответов (0 = строго, 1 = творчески)"
        )
    
    with tab3:
        st.subheader("📊 Статус бота")
        
        # Информация о последнем обновлении
        if "last_updated" in instruction_data:
            last_update = instruction_data["last_updated"]
            if last_update:
                st.info(f"📅 Последнее обновление инструкций: {last_update}")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔍 Проверить статус бота", use_container_width=True):
                try:
                    import requests
                    response = requests.get(f"{BOT_URL}/", timeout=10)
                    if response.status_code == 200:
                        st.success("✅ Бот онлайн и работает")
                        # Дополнительная проверка debug endpoint если есть
                        try:
                            debug_response = requests.get(f"{BOT_URL}/debug/status", timeout=5)
                            if debug_response.status_code == 200:
                                debug_data = debug_response.json()
                                st.json(debug_data)
                        except:
                            pass
                    else:
                        st.error(f"❌ HTTP {response.status_code}")
                except Exception as e:
                    st.error(f"❌ Не удается подключиться к боту: {e}")
        
        with col2:
            if st.button("🔄 Применить изменения мгновенно", use_container_width=True):
                try:
                    import requests
                    
                    # Подготавливаем данные для отправки
                    update_data = {
                        "system_instruction": system_instruction,
                        "welcome_message": welcome_message,
                        "settings": {
                            "voice_enabled": voice_enabled,
                            "memory_enabled": memory_enabled,
                            "debug_mode": debug_mode,
                            "max_memory_messages": max_memory_messages,
                            "response_temperature": response_temperature
                        }
                    }
                    
                    # Отправляем через новый API endpoint
                    response = requests.post(
                        f"{BOT_URL}/admin/update-instructions", 
                        json=update_data,
                        headers={"Content-Type": "application/json"},
                        timeout=15
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        if data.get("status") == "success":
                            st.success("✅ Изменения применены мгновенно! Бот использует новые инструкции.")
                            st.info(f"🕐 Обновлено: {data.get('new_updated', 'неизвестно')}")
                        else:
                            st.error(f"❌ Ошибка: {data.get('error', 'Неизвестная ошибка')}")
                    else:
                        st.error(f"❌ HTTP {response.status_code}: {response.text}")
                        
                except Exception as e:
                    st.error(f"❌ Ошибка подключения к боту: {e}")
    
    st.markdown("---")
    
    if st.button("🚀 Сохранить все изменения", type="primary", use_container_width=True):
        new_instruction_data = {
            "system_instruction": system_instruction,
            "welcome_message": welcome_message,
            "settings": {
                "voice_enabled": voice_enabled,
                "memory_enabled": memory_enabled,
                "debug_mode": debug_mode,
                "max_memory_messages": max_memory_messages,
                "response_temperature": response_temperature
            }
        }
        
        try:
            # Сохраняем локально (для backup) + GitHub push
            if save_instruction(new_instruction_data.copy()):
                st.success("✅ Инструкции сохранены локально!")
            
            # Главное - отправляем напрямую на бот
            import requests
            response = requests.post(
                f"{BOT_URL}/admin/update-instructions", 
                json=new_instruction_data,
                headers={"Content-Type": "application/json"},
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    st.success("🎉 Изменения применены мгновенно! Бот использует новые инструкции.")
                    st.info(f"🕐 Обновлено: {data.get('new_updated', 'неизвестно')}")
                    st.balloons()
                else:
                    st.error(f"❌ Ошибка применения: {data.get('error', 'Неизвестная ошибка')}")
            else:
                st.error(f"❌ HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            st.error(f"❌ Ошибка: {e}")


if __name__ == "__main__":
    main()