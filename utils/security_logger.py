import logging
import os
from datetime import datetime
from typing import Optional, Dict, Any

class SecurityLogger:
    """Специализированный логгер для событий безопасности"""
    
    def __init__(self, log_file: str = "security.log"):
        self.log_file = log_file
        self.logger = self._setup_security_logger()
    
    def _setup_security_logger(self) -> logging.Logger:
        """Настройка логгера безопасности"""
        logger = logging.getLogger('security')
        logger.setLevel(logging.INFO)
        
        # Очищаем существующие обработчики
        logger.handlers.clear()
        
        # Создаем форматтер для безопасности
        formatter = logging.Formatter(
            '%(asctime)s - SECURITY - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Обработчик для файла безопасности
        file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        
        # Обработчик для консоли (только критические события)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)
        console_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        return logger
    
    def log_failed_login(self, user_id: int, username: str, reason: str, ip: str = "unknown"):
        """Логирование неудачной попытки входа"""
        self.logger.warning(
            f"FAILED_LOGIN - User: {user_id} (@{username}) - Reason: {reason} - IP: {ip}"
        )
    
    def log_suspicious_activity(self, user_id: int, username: str, activity: str, details: str):
        """Логирование подозрительной активности"""
        self.logger.warning(
            f"SUSPICIOUS_ACTIVITY - User: {user_id} (@{username}) - Activity: {activity} - Details: {details}"
        )
    
    def log_rate_limit_exceeded(self, user_id: int, username: str, limit: int, time_window: int):
        """Логирование превышения rate limit"""
        self.logger.info(
            f"RATE_LIMIT_EXCEEDED - User: {user_id} (@{username}) - Limit: {limit}/{time_window}s"
        )
    
    def log_user_banned(self, user_id: int, username: str, reason: str, banned_by: str = "system"):
        """Логирование бана пользователя"""
        self.logger.warning(
            f"USER_BANNED - User: {user_id} (@{username}) - Reason: {reason} - Banned by: {banned_by}"
        )
    
    def log_admin_action(self, admin_id: int, username: str, action: str, target: str = None):
        """Логирование действий администратора"""
        target_info = f" - Target: {target}" if target else ""
        self.logger.info(
            f"ADMIN_ACTION - Admin: {admin_id} (@{username}) - Action: {action}{target_info}"
        )
    
    def log_unauthorized_access(self, user_id: int, username: str, resource: str, action: str):
        """Логирование несанкционированного доступа"""
        self.logger.warning(
            f"UNAUTHORIZED_ACCESS - User: {user_id} (@{username}) - Resource: {resource} - Action: {action}"
        )
    
    def log_input_validation_failed(self, user_id: int, username: str, input_type: str, value: str, error: str):
        """Логирование неудачной валидации входных данных"""
        # Маскируем чувствительные данные
        masked_value = self._mask_sensitive_data(value, input_type)
        self.logger.info(
            f"INPUT_VALIDATION_FAILED - User: {user_id} (@{username}) - Type: {input_type} - Value: {masked_value} - Error: {error}"
        )
    
    def log_security_event(self, event_type: str, user_id: int, username: str, details: Dict[str, Any]):
        """Логирование общего события безопасности"""
        details_str = " - ".join([f"{k}: {v}" for k, v in details.items()])
        self.logger.info(
            f"SECURITY_EVENT - Type: {event_type} - User: {user_id} (@{username}) - Details: {details_str}"
        )
    
    def log_critical_security_breach(self, description: str, user_id: int = None, username: str = None, additional_data: Dict[str, Any] = None):
        """Логирование критического нарушения безопасности"""
        user_info = f" - User: {user_id} (@{username})" if user_id else ""
        additional_info = f" - Additional: {additional_data}" if additional_data else ""
        self.logger.critical(
            f"CRITICAL_SECURITY_BREACH - {description}{user_info}{additional_info}"
        )
    
    def _mask_sensitive_data(self, value: str, data_type: str) -> str:
        """Маскирование чувствительных данных в логах"""
        if not value:
            return "empty"
        
        if data_type in ["phone", "contact"]:
            # Маскируем номер телефона
            if len(value) > 4:
                return value[:2] + "*" * (len(value) - 4) + value[-2:]
            return "*" * len(value)
        
        elif data_type in ["name", "parent_name", "student_name"]:
            # Маскируем имена (показываем только первую букву)
            if len(value) > 1:
                return value[0] + "*" * (len(value) - 1)
            return "*"
        
        elif data_type == "age":
            # Возраст можно показывать полностью
            return value
        
        else:
            # Для остальных типов маскируем половину
            if len(value) > 2:
                return value[:len(value)//2] + "*" * (len(value) - len(value)//2)
            return "*" * len(value)
    
    def get_security_report(self, hours: int = 24) -> Dict[str, int]:
        """Получение отчета по событиям безопасности за последние N часов"""
        try:
            from datetime import datetime, timedelta
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            events = {
                "failed_logins": 0,
                "suspicious_activities": 0,
                "rate_limit_exceeded": 0,
                "user_bans": 0,
                "unauthorized_access": 0,
                "input_validation_failed": 0
            }
            
            if not os.path.exists(self.log_file):
                return events
            
            with open(self.log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        # Парсим время из лога
                        log_time_str = line.split(' - ')[0]
                        log_time = datetime.strptime(log_time_str, '%Y-%m-%d %H:%M:%S')
                        
                        if log_time >= cutoff_time:
                            if "FAILED_LOGIN" in line:
                                events["failed_logins"] += 1
                            elif "SUSPICIOUS_ACTIVITY" in line:
                                events["suspicious_activities"] += 1
                            elif "RATE_LIMIT_EXCEEDED" in line:
                                events["rate_limit_exceeded"] += 1
                            elif "USER_BANNED" in line:
                                events["user_bans"] += 1
                            elif "UNAUTHORIZED_ACCESS" in line:
                                events["unauthorized_access"] += 1
                            elif "INPUT_VALIDATION_FAILED" in line:
                                events["input_validation_failed"] += 1
                    except:
                        continue
            
            return events
            
        except Exception as e:
            self.logger.error(f"Error generating security report: {e}")
            return {}

# Глобальный экземпляр логгера безопасности
security_logger = SecurityLogger() 