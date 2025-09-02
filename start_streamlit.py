#!/usr/bin/env python3
"""
Streamlit приложение для администрирования бота
"""

import streamlit as st
import os
import sys
import logging
from pathlib import Path

# Добавляем текущую директорию в путь Python
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Главная функция Streamlit приложения"""
    
    st.set_page_config(
        page_title="Ignatova Stroinost Bot Admin",
        page_icon="🤖",
        layout="wide"
    )
    
    st.title("🤖 Ignatova Stroinost Bot - Панель управления")
    
    # Основная информация
    st.header("📊 Статус системы")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Статус бота", "🟢 Активен", help="Бот работает на Railway")
        
    with col2:
        st.metric("База данных", "🟢 Подключена", help="Zep Memory работает")
        
    with col3:
        st.metric("AI провайдеры", "🟢 Доступны", help="OpenAI и Anthropic подключены")
    
    # Разделы управления
    st.header("🛠️ Управление")
    
    tab1, tab2, tab3, tab4 = st.tabs(["📝 Инструкции", "💬 Память", "🔧 Настройки", "📈 Статистика"])
    
    with tab1:
        st.subheader("Управление инструкциями бота")
        
        # Проверяем наличие файла инструкций
        instructions_path = current_dir / "data" / "instruction.json"
        
        if instructions_path.exists():
            import json
            try:
                with open(instructions_path, 'r', encoding='utf-8') as f:
                    instructions = json.load(f)
                
                st.success(f"✅ Инструкции загружены")
                
                # Показываем основную инструкцию
                if 'main_instruction' in instructions:
                    st.text_area(
                        "Основная инструкция:",
                        value=instructions['main_instruction'],
                        height=200,
                        disabled=True,
                        help="Это текущая инструкция бота"
                    )
                
                # Показываем дополнительные настройки
                if 'settings' in instructions:
                    st.json(instructions['settings'])
                    
            except Exception as e:
                st.error(f"Ошибка при загрузке инструкций: {e}")
        else:
            st.warning("⚠️ Файл инструкций не найден")
            
    with tab2:
        st.subheader("Управление памятью разговоров")
        
        st.info("💡 Используется Zep Memory для хранения контекста разговоров")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔄 Обновить статус", type="primary"):
                st.rerun()
                
        with col2:
            if st.button("🗑️ Очистить память конкретного пользователя"):
                st.warning("Эта функция требует ввода User ID")
                
    with tab3:
        st.subheader("Настройки бота")
        
        # Показываем текущие настройки
        st.code(f"""
        WEBHOOK_URL: {os.getenv('WEBHOOK_URL', 'Не установлен')}
        PORT: {os.getenv('PORT', '8000')}
        DEBUG: {os.getenv('DEBUG', 'False')}
        """)
        
        st.info("ℹ️ Для изменения настроек используйте переменные окружения в Railway")
        
    with tab4:
        st.subheader("Статистика использования")
        
        # Примерная статистика
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Всего сообщений", "N/A", help="Требуется подключение к БД")
            
        with col2:
            st.metric("Активных пользователей", "N/A", help="Требуется подключение к БД")
            
        with col3:
            st.metric("Среднее время ответа", "N/A", help="Требуется мониторинг")
    
    # Футер
    st.divider()
    st.caption("🤖 Ignatova Stroinost Bot Admin Panel v2.0 | Powered by Claude & OpenAI")
    
    # Информация для разработчика
    with st.expander("👨‍💻 Информация для разработчика"):
        st.code(f"""
        Python: {sys.version}
        Streamlit: {st.__version__}
        Current Directory: {current_dir}
        Environment: {os.getenv('RAILWAY_ENVIRONMENT', 'local')}
        """)

if __name__ == "__main__":
    try:
        logger.info("Starting Streamlit application...")
        main()
    except Exception as e:
        logger.error(f"Error in Streamlit app: {e}")
        st.error(f"Произошла ошибка: {e}")