# === utils/common.py ===
# Централизованные импорты и общие функции

from utils.menu import get_main_menu, get_admin_menu
from config import ADMIN_ID

# Общие функции для валидации
def validate_text_length(text, max_length=100, field_name="текст"):
    """Проверяет длину текста"""
    if not text or not isinstance(text, str):
        return False, f"{field_name} должен быть строкой"
    
    if len(text.strip()) == 0:
        return False, f"{field_name} не может быть пустым"
    
    if len(text) > max_length:
        return False, f"{field_name} слишком длинный (максимум {max_length} символов)"
    
    return True, text.strip()

def sanitize_text(text):
    """Очищает текст от потенциально опасных символов"""
    if not text:
        return ""
    
    # Убираем HTML-теги и экранируем специальные символы
    import re
    text = re.sub(r'<[^>]+>', '', text)  # Убираем HTML теги
    text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    return text.strip()

def is_admin(user_id):
    return str(user_id) == str(ADMIN_ID) 