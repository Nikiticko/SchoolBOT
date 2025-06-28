import re
import time
from typing import Dict, Set, Optional, Any
from config import MAX_MESSAGE_LENGTH, MAX_NAME_LENGTH, RATE_LIMIT_PER_MINUTE, BAN_THRESHOLD
from utils.logger import log_error
from utils.security_logger import security_logger
from utils.exceptions import (
    SecurityException, UserBannedException, RateLimitException, 
    ValidationException, handle_exception
)
from state.state_manager import state_manager

class SecurityManager:
    """Менеджер безопасности для валидации и rate limiting"""
    
    def __init__(self):
        # Используем StateManager вместо локальных переменных
        self.logger = security_logger
    
    def validate_message_length(self, text: str, max_length: int = MAX_MESSAGE_LENGTH) -> bool:
        """Валидация длины сообщения"""
        if not text or not isinstance(text, str):
            return False
        return len(text.strip()) <= max_length
    
    def validate_name(self, name: str, max_length: int = MAX_NAME_LENGTH) -> tuple[bool, str]:
        """Валидация имени пользователя"""
        if not name or not isinstance(name, str):
            return False, "Имя не может быть пустым"
        
        name = name.strip()
        if len(name) > max_length:
            return False, f"Имя слишком длинное (максимум {max_length} символов)"
        
        # Проверяем на допустимые символы (кириллица, латиница, пробелы, дефисы)
        if not re.match(r'^[а-яёa-z\s\-]+$', name.lower()):
            return False, "Имя содержит недопустимые символы"
        
        # Проверяем на минимальную длину
        if len(name) < 2:
            return False, "Имя слишком короткое"
        
        return True, ""
    
    def validate_age(self, age: str) -> tuple[bool, str]:
        """Валидация возраста"""
        if not age or not isinstance(age, str):
            return False, "Возраст не может быть пустым"
        
        age = age.strip()
        if not age.isdigit():
            return False, "Возраст должен быть числом"
        
        age_num = int(age)
        if age_num < 3 or age_num > 100:
            return False, "Возраст должен быть от 3 до 100 лет"
        
        return True, ""
    
    def validate_phone(self, phone: str) -> tuple[bool, str]:
        """Валидация номера телефона"""
        if not phone:
            return True, ""  # Телефон необязателен
        
        phone = phone.strip()
        # Убираем все кроме цифр
        digits_only = re.sub(r'\D', '', phone)
        
        if len(digits_only) < 10 or len(digits_only) > 15:
            return False, "Неверный формат номера телефона"
        
        return True, ""
    
    def validate_telegram_username(self, username: str) -> tuple[bool, str]:
        """Валидация Telegram username"""
        if not username:
            return True, ""  # Username необязателен
        
        username = username.strip()
        if not username.startswith('@'):
            username = '@' + username
        
        # Telegram username: 5-32 символа, буквы, цифры, подчеркивания
        if not re.match(r'^@[a-zA-Z0-9_]{5,32}$', username):
            return False, "Неверный формат username"
        
        return True, ""
    
    def check_rate_limit(self, user_id: int) -> tuple[bool, int]:
        """Проверка rate limit для пользователя"""
        current_time = time.time()
        
        # Получаем данные из StateManager
        rate_limit_data = state_manager.get_rate_limit_data(user_id)
        
        # Удаляем старые записи (старше 1 минуты)
        rate_limit_data = [
            timestamp for timestamp in rate_limit_data
            if current_time - timestamp < 60
        ]
        
        # Проверяем лимит
        if len(rate_limit_data) >= RATE_LIMIT_PER_MINUTE:
            remaining_time = int(60 - (current_time - rate_limit_data[0]))
            
            # Логируем превышение rate limit
            security_logger.log_rate_limit_exceeded(
                user_id, 
                "unknown", 
                RATE_LIMIT_PER_MINUTE, 
                60
            )
            
            return False, remaining_time
        
        # Добавляем текущий запрос
        rate_limit_data.append(current_time)
        state_manager.set_rate_limit_data(user_id, rate_limit_data)
        return True, 0
    
    def is_user_banned(self, user_id: int) -> bool:
        """Проверка, забанен ли пользователь"""
        return state_manager.is_user_banned(user_id)
    
    def ban_user(self, user_id: int, reason: str = "Нарушение правил"):
        """Бан пользователя"""
        state_manager.add_banned_user(user_id)
        
        # Логируем бан
        security_logger.log_user_banned(user_id, "unknown", reason, "system")
        
        print(f"🚫 Пользователь {user_id} заблокирован. Причина: {reason}")
    
    def record_suspicious_activity(self, user_id: int, activity_type: str):
        """Запись подозрительной активности"""
        current_count = state_manager.get_suspicious_count(user_id)
        new_count = current_count + 1
        state_manager.increment_suspicious_count(user_id)
        
        # Логируем подозрительную активность
        security_logger.log_suspicious_activity(
            user_id, 
            "unknown", 
            activity_type, 
            f"Count: {new_count}/{BAN_THRESHOLD}"
        )
        
        if new_count >= BAN_THRESHOLD:
            self.ban_user(user_id, f"Множественные нарушения: {activity_type}")
            return True
        
        return False
    
    def sanitize_input(self, text: str) -> str:
        """Санитизация входных данных"""
        if not text:
            return ""
        
        # Убираем потенциально опасные символы
        text = re.sub(r'[<>"\']', '', text)
        # Убираем множественные пробелы
        text = re.sub(r'\s+', ' ', text)
        # Обрезаем пробелы
        return text.strip()
    
    def validate_course_name(self, course_name: str) -> tuple[bool, str]:
        """Валидация названия курса"""
        if not course_name or not isinstance(course_name, str):
            return False, "Название курса не может быть пустым"
        
        course_name = course_name.strip()
        if len(course_name) > 100:
            return False, "Название курса слишком длинное"
        
        if len(course_name) < 3:
            return False, "Название курса слишком короткое"
        
        return True, ""

# Глобальный экземпляр менеджера безопасности
security_manager = SecurityManager()

def validate_user_input(text: str, input_type: str = "message") -> tuple[bool, str]:
    """Универсальная валидация пользовательского ввода"""
    try:
        if not text or not isinstance(text, str):
            return False, "Пустой или неверный тип данных"
        
        # Санитизация
        sanitized_text = security_manager.sanitize_input(text)
        
        if input_type == "name":
            return security_manager.validate_name(sanitized_text)
        elif input_type == "age":
            return security_manager.validate_age(sanitized_text)
        elif input_type == "phone":
            return security_manager.validate_phone(sanitized_text)
        elif input_type == "username":
            return security_manager.validate_telegram_username(sanitized_text)
        elif input_type == "course":
            return security_manager.validate_course_name(sanitized_text)
        else:
            return security_manager.validate_message_length(sanitized_text)
    
    except Exception as e:
        # Логируем ошибку валидации
        log_error(security_logger, e, f"Validation error for type: {input_type}")
        return False, "Ошибка валидации данных"

def check_user_security(user_id: int, action_type: str = "message") -> tuple[bool, str]:
    """Проверка безопасности пользователя"""
    try:
        # Проверка бана
        if security_manager.is_user_banned(user_id):
            raise UserBannedException(user_id)
        
        # Проверка rate limit
        allowed, remaining_time = security_manager.check_rate_limit(user_id)
        if not allowed:
            raise RateLimitException(user_id, remaining_time)
        
        return True, ""
        
    except (UserBannedException, RateLimitException) as e:
        # Возвращаем ошибку для обработки
        return False, str(e)
    except Exception as e:
        # Логируем неожиданную ошибку
        log_error(security_logger, e, f"Security check error for user {user_id}")
        return False, "Ошибка проверки безопасности"

def log_security_event(user_id: int, username: str, event_type: str, details: Dict[str, Any] = None):
    """Логирование события безопасности"""
    try:
        security_logger.log_security_event(user_id, username, event_type, details or {})
    except Exception as e:
        log_error(security_logger, e, f"Security event logging error for user {user_id}") 