# state/users.py
"""
Модуль для работы с данными пользователей
Использует новый StateManager для безопасного хранения состояний
"""

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
