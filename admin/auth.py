import streamlit as st
import hashlib
import os
from datetime import datetime, timedelta

# Простой пароль для демо (в продакшне использовать более надежную систему)
ADMIN_PASSWORD_HASH = "5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8"  # "password"

def hash_password(password: str) -> str:
    """Хеширование пароля"""
    return hashlib.sha256(password.encode()).hexdigest()

def check_password():
    """Проверка пароля для доступа к админ панели"""
    
    def password_entered():
        """Проверяет введенный пароль"""
        if hash_password(st.session_state["password"]) == ADMIN_PASSWORD_HASH:
            st.session_state["password_correct"] = True
            st.session_state["login_time"] = datetime.now()
            del st.session_state["password"]  # Не сохраняем пароль в сессии
        else:
            st.session_state["password_correct"] = False

    # Проверяем, авторизован ли пользователь
    if st.session_state.get("password_correct", False):
        # Проверяем, не истекла ли сессия (24 часа)
        login_time = st.session_state.get("login_time")
        if login_time and datetime.now() - login_time > timedelta(hours=24):
            st.session_state["password_correct"] = False
            st.session_state["login_time"] = None
            st.warning("Сессия истекла. Пожалуйста, войдите заново.")
            return False
        return True

    # Показываем форму входа
    st.markdown("## 🔐 Вход в админ панель")
    st.text_input(
        "Пароль", 
        type="password", 
        on_change=password_entered, 
        key="password"
    )
    
    if st.session_state.get("password_correct", None) is False:
        st.error("😕 Неверный пароль")
    
    return False

def logout():
    """Выход из системы"""
    st.session_state["password_correct"] = False
    st.session_state["login_time"] = None
    st.rerun()

def show_auth_info():
    """Показывает информацию об авторизации в боковой панели"""
    if st.session_state.get("password_correct", False):
        login_time = st.session_state.get("login_time")
        if login_time:
            st.sidebar.success(f"✅ Авторизован\n{login_time.strftime('%d.%m.%Y %H:%M')}")
        
        if st.sidebar.button("🚪 Выйти"):
            logout()