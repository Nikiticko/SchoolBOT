# state/users.py
"""
Модуль для работы с данными пользователей
Использует новый StateManager для безопасного хранения состояний
"""

import time
from state.state_manager import state_manager

# Функции для обратной совместимости
def get_user_data(user_id: int):
    """Получает данные пользователя"""
    return state_manager.get_user_data(user_id)

def set_user_data(user_id: int, data: dict):
    """Устанавливает данные пользователя"""
    state_manager.set_user_data(user_id, data)

def update_user_data(user_id: int, **kwargs):
    """Обновляет данные пользователя"""
    state_manager.update_user_data(user_id, **kwargs)

def clear_user_data(user_id: int):
    """Очищает данные пользователя"""
    state_manager.clear_user_data(user_id)

# ИСПРАВЛЕНО: Новые функции для работы с состоянием регистрации
def start_registration(user_id: int):
    """Начинает процесс регистрации"""
    state_manager.set_user_data(user_id, {
        "in_progress": True,
        "stage": "parent_name",
        "started_at": time.time()
    })

def is_registration_in_progress(user_id: int) -> bool:
    """Проверяет, идет ли процесс регистрации"""
    data = state_manager.get_user_data(user_id)
    return data.get("in_progress", False)

def get_registration_stage(user_id: int) -> str:
    """Получает текущий этап регистрации"""
    data = state_manager.get_user_data(user_id)
    return data.get("stage", "")

def update_registration_stage(user_id: int, stage: str):
    """Обновляет этап регистрации"""
    state_manager.update_user_data(user_id, stage=stage)

def get_registration_start_time(user_id: int) -> float:
    """Получает время начала регистрации"""
    data = state_manager.get_user_data(user_id)
    return data.get("started_at", 0)

def cleanup_expired_registrations(timeout_minutes: int = 30):
    """Очищает просроченные регистрации"""
    current_time = time.time()
    timeout_seconds = timeout_minutes * 60
    
    # Получаем всех пользователей с активными регистрациями
    all_user_data = state_manager._state["user_data"]
    expired_users = []
    
    for user_id_str, data in all_user_data.items():
        if data.get("in_progress") and data.get("started_at"):
            if current_time - data["started_at"] > timeout_seconds:
                expired_users.append(int(user_id_str))
    
    # Очищаем просроченные регистрации
    for user_id in expired_users:
        state_manager.clear_user_data(user_id)
    
    return len(expired_users)

# Для обратной совместимости с существующим кодом
user_data = {}  # Пустой словарь для совместимости
chat_contact_map = {}  # Пустой словарь для совместимости
pending = {}  # Пустой словарь для совместимости
writing_ids = set()  # Пустое множество для совместимости

# Функции для работы с pending
def add_pending(user_id: int, data: dict):
    """Добавляет ожидающее уведомление"""
    state_manager.add_pending(user_id, data)

def get_pending(user_id: int):
    """Получает ожидающее уведомление"""
    return state_manager.get_pending(user_id)

def remove_pending(user_id: int):
    """Удаляет ожидающее уведомление"""
    state_manager.remove_pending(user_id)

def get_all_pending():
    """Получает все ожидающие уведомления"""
    return state_manager.get_all_pending()

# Функции для работы с writing_ids
def add_writing_id(app_id: int):
    """Добавляет ID заявки в обработку"""
    state_manager.add_writing_id(app_id)

def remove_writing_id(app_id: int):
    """Удаляет ID заявки из обработки"""
    state_manager.remove_writing_id(app_id)

def is_writing_id(app_id: int) -> bool:
    """Проверяет, обрабатывается ли заявка"""
    return state_manager.is_writing_id(app_id)

def get_writing_ids():
    """Получает все ID заявок в обработке"""
    return state_manager._state["writing_ids"].copy()

# Функции для работы с chat_contact_map
def get_chat_contact(chat_id: int):
    """Получает контакт для чата"""
    return state_manager.get_chat_contact(chat_id)

def set_chat_contact(chat_id: int, contact: str):
    """Устанавливает контакт для чата"""
    state_manager.set_chat_contact(chat_id, contact)

def remove_chat_contact(chat_id: int):
    """Удаляет контакт для чата"""
    state_manager.remove_chat_contact(chat_id)
