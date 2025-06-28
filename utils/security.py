import re
import time
from typing import Dict, Set, Optional, Any
from config import MAX_MESSAGE_LENGTH, MAX_NAME_LENGTH, RATE_LIMIT_PER_MINUTE, BAN_THRESHOLD
from utils.logger import log_error
from utils.security_logger import security_logger

class SecurityManager:
    """Менеджер безопасности для валидации и rate limiting"""
    
    def __init__(self):
        self.rate_limit_data: Dict[int, list] = {}  # user_id -> [timestamps]
        self.banned_users: Set[int] = set()
        self.suspicious_activities: Dict[int, int] = {}  # user_id -> count
    
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
        
        if user_id not in self.rate_limit_data:
            self.rate_limit_data[user_id] = []
        
        # Удаляем старые записи (старше 1 минуты)
        self.rate_limit_data[user_id] = [
            timestamp for timestamp in self.rate_limit_data[user_id]
            if current_time - timestamp < 60
        ]
        
        # Проверяем лимит
        if len(self.rate_limit_data[user_id]) >= RATE_LIMIT_PER_MINUTE:
            remaining_time = int(60 - (current_time - self.rate_limit_data[user_id][0]))
            
            # Логируем превышение rate limit
            security_logger.log_rate_limit_exceeded(
                user_id, 
                "unknown", 
                RATE_LIMIT_PER_MINUTE, 
                60
            )
            
            return False, remaining_time
        
        # Добавляем текущий запрос
        self.rate_limit_data[user_id].append(current_time)
        return True, 0
    
    def is_user_banned(self, user_id: int) -> bool:
        """Проверка, забанен ли пользователь"""
        return user_id in self.banned_users
    
    def ban_user(self, user_id: int, reason: str = "Нарушение правил"):
        """Бан пользователя"""
        self.banned_users.add(user_id)
        
        # Логируем бан
        security_logger.log_user_banned(user_id, "unknown", reason, "system")
        
        print(f"🚫 Пользователь {user_id} заблокирован. Причина: {reason}")
    
    def record_suspicious_activity(self, user_id: int, activity_type: str):
        """Запись подозрительной активности"""
        if user_id not in self.suspicious_activities:
            self.suspicious_activities[user_id] = 0
        
        self.suspicious_activities[user_id] += 1
        
        # Логируем подозрительную активность
        security_logger.log_suspicious_activity(
            user_id, 
            "unknown", 
            activity_type, 
            f"Count: {self.suspicious_activities[user_id]}/{BAN_THRESHOLD}"
        )
        
        if self.suspicious_activities[user_id] >= BAN_THRESHOLD:
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
        log_error(None, e, f"Error in validate_user_input for type {input_type}")
        return False, "Ошибка валидации"

def check_user_security(user_id: int, action_type: str = "message") -> tuple[bool, str]:
    """Проверка безопасности пользователя"""
    try:
        # Проверка бана
        if security_manager.is_user_banned(user_id):
            return False, "Вы заблокированы"
        
        # Проверка rate limit
        rate_ok, remaining_time = security_manager.check_rate_limit(user_id)
        if not rate_ok:
            return False, f"Слишком много запросов. Попробуйте через {remaining_time} секунд"
        
        return True, ""
    
    except Exception as e:
        log_error(None, e, f"Error in check_user_security for user {user_id}")
        return False, "Ошибка проверки безопасности"

def log_security_event(user_id: int, username: str, event_type: str, details: Dict[str, Any] = None):
    """Логирование события безопасности"""
    try:
        if details is None:
            details = {}
        security_logger.log_security_event(event_type, user_id, username, details)
    except Exception as e:
        log_error(None, e, f"Error logging security event for user {user_id}") 