"""
Кастомные исключения для проекта
"""

class BotException(Exception):
    """Базовое исключение для всех ошибок бота"""
    
    def __init__(self, message: str, error_code: str = None, details: dict = None):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)
    
    def __str__(self):
        if self.error_code:
            return f"[{self.error_code}] {self.message}"
        return self.message

class DatabaseException(BotException):
    """Исключение для ошибок базы данных"""
    
    def __init__(self, message: str, operation: str = None, table: str = None):
        super().__init__(message, "DB_ERROR", {
            "operation": operation,
            "table": table
        })

class DatabaseConnectionException(DatabaseException):
    """Исключение для ошибок подключения к БД"""
    
    def __init__(self, message: str, db_path: str = None):
        super().__init__(message, "DB_CONNECTION_ERROR", {
            "db_path": db_path
        })

class DatabaseMigrationException(DatabaseException):
    """Исключение для ошибок миграции БД"""
    
    def __init__(self, message: str, migration_step: str = None):
        super().__init__(message, "DB_MIGRATION_ERROR", {
            "migration_step": migration_step
        })

class SecurityException(BotException):
    """Исключение для ошибок безопасности"""
    
    def __init__(self, message: str, user_id: int = None, action: str = None):
        super().__init__(message, "SECURITY_ERROR", {
            "user_id": user_id,
            "action": action
        })

class UserBannedException(SecurityException):
    """Исключение для забаненных пользователей"""
    
    def __init__(self, user_id: int, reason: str = None):
        super().__init__(
            f"Пользователь {user_id} заблокирован",
            "USER_BANNED",
            {"user_id": user_id, "reason": reason}
        )

class RateLimitException(SecurityException):
    """Исключение для превышения rate limit"""
    
    def __init__(self, user_id: int, remaining_time: int = None):
        super().__init__(
            f"Превышен лимит запросов для пользователя {user_id}",
            "RATE_LIMIT_EXCEEDED",
            {"user_id": user_id, "remaining_time": remaining_time}
        )

class ValidationException(BotException):
    """Исключение для ошибок валидации"""
    
    def __init__(self, message: str, field: str = None, value: str = None):
        super().__init__(message, "VALIDATION_ERROR", {
            "field": field,
            "value": value
        })

class ConfigurationException(BotException):
    """Исключение для ошибок конфигурации"""
    
    def __init__(self, message: str, config_key: str = None):
        super().__init__(message, "CONFIG_ERROR", {
            "config_key": config_key
        })

class TelegramAPIException(BotException):
    """Исключение для ошибок Telegram API"""
    
    def __init__(self, message: str, api_method: str = None, error_code: int = None):
        super().__init__(message, "TELEGRAM_API_ERROR", {
            "api_method": api_method,
            "telegram_error_code": error_code
        })

class StateException(BotException):
    """Исключение для ошибок управления состоянием"""
    
    def __init__(self, message: str, state_key: str = None):
        super().__init__(message, "STATE_ERROR", {
            "state_key": state_key
        })

class HandlerException(BotException):
    """Исключение для ошибок обработчиков"""
    
    def __init__(self, message: str, handler_name: str = None, user_id: int = None):
        super().__init__(message, "HANDLER_ERROR", {
            "handler_name": handler_name,
            "user_id": user_id
        })

class MonitoringException(BotException):
    """Исключение для ошибок мониторинга"""
    
    def __init__(self, message: str, monitoring_type: str = None):
        super().__init__(message, "MONITORING_ERROR", {
            "monitoring_type": monitoring_type
        })

class RegistrationException(BotException):
    """Исключение для ошибок регистрации"""
    def __init__(self, message: str, error_code: str = "REGISTRATION_ERROR", details: dict = None):
        super().__init__(message, error_code, details)

class RegistrationTimeoutException(RegistrationException):
    """Исключение для истечения времени регистрации"""
    
    def __init__(self, user_id: int, timeout_minutes: int = 30):
        super().__init__(
            f"Время регистрации истекло ({timeout_minutes} минут)",
            "REGISTRATION_TIMEOUT",
            {"user_id": user_id, "timeout_minutes": timeout_minutes}
        )

class DuplicateApplicationException(RegistrationException):
    """Исключение для дублирования заявок"""
    
    def __init__(self, user_id: int, existing_app_id: int = None):
        super().__init__(
            "У вас уже есть активная заявка",
            "DUPLICATE_APPLICATION",
            {"user_id": user_id, "existing_app_id": existing_app_id}
        )

class InvalidRegistrationStageException(RegistrationException):
    """Исключение для неверного этапа регистрации"""
    
    def __init__(self, user_id: int, expected_stage: str, actual_stage: str):
        super().__init__(
            f"Неверный этап регистрации: ожидался {expected_stage}, получен {actual_stage}",
            "INVALID_REGISTRATION_STAGE",
            {"user_id": user_id, "expected_stage": expected_stage, "actual_stage": actual_stage}
        )

# Функции для создания исключений
def create_database_error(message: str, operation: str = None, table: str = None) -> DatabaseException:
    """Создает исключение для ошибки БД"""
    return DatabaseException(message, operation, table)

def create_security_error(message: str, user_id: int = None, action: str = None) -> SecurityException:
    """Создает исключение для ошибки безопасности"""
    return SecurityException(message, user_id, action)

def create_validation_error(message: str, field: str = None, value: str = None) -> ValidationException:
    """Создает исключение для ошибки валидации"""
    return ValidationException(message, field, value)

def create_telegram_error(message: str, api_method: str = None, error_code: int = None) -> TelegramAPIException:
    """Создает исключение для ошибки Telegram API"""
    return TelegramAPIException(message, api_method, error_code)

# Функция для обработки исключений
def handle_exception(exception: Exception, logger, context: str = None) -> str:
    """
    Обрабатывает исключение и возвращает сообщение для пользователя
    
    Args:
        exception: Исключение для обработки
        logger: Логгер для записи ошибки
        context: Контекст, в котором произошла ошибка
    
    Returns:
        Сообщение для пользователя
    """
    
    if isinstance(exception, BotException):
        # Логируем кастомное исключение
        logger.error(f"[{exception.error_code}] {exception.message}", extra={
            "context": context,
            "details": exception.details
        })
        
        # Возвращаем понятное сообщение для пользователя
        if isinstance(exception, UserBannedException):
            return "🚫 Вы заблокированы. Обратитесь к администратору."
        elif isinstance(exception, RateLimitException):
            remaining = exception.details.get("remaining_time", 0)
            return f"⏳ Слишком много запросов. Попробуйте через {remaining} секунд."
        elif isinstance(exception, ValidationException):
            return f"❌ Ошибка валидации: {exception.message}"
        elif isinstance(exception, DatabaseException):
            return "❌ Ошибка базы данных. Попробуйте позже."
        elif isinstance(exception, ConfigurationException):
            return "❌ Ошибка конфигурации. Обратитесь к администратору."
        elif isinstance(exception, TelegramAPIException):
            return "❌ Ошибка Telegram. Попробуйте позже."
        elif isinstance(exception, RegistrationTimeoutException):
            timeout = exception.details.get("timeout_minutes", 30)
            return f"⏰ Время регистрации истекло ({timeout} минут). Начните заново."
        elif isinstance(exception, DuplicateApplicationException):
            return "⚠️ У вас уже есть активная заявка. Дождитесь ответа администратора."
        elif isinstance(exception, InvalidRegistrationStageException):
            return "⚠️ Неверный этап регистрации. Начните заново."
        elif isinstance(exception, RegistrationException):
            return f"❌ Ошибка регистрации: {exception.message}"
        else:
            return "❌ Произошла ошибка. Попробуйте позже."
    
    else:
        # Логируем стандартное исключение
        logger.error(f"Неожиданная ошибка: {str(exception)}", extra={
            "context": context,
            "exception_type": type(exception).__name__
        })
        return "❌ Произошла неожиданная ошибка. Попробуйте позже." 