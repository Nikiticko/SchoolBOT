from telebot import TeleBot
from telebot.types import Message, CallbackQuery
from utils.security import check_user_security, security_manager
from utils.logger import log_error, log_user_action
from typing import Callable, Any
import functools
from config import ADMIN_ID

def security_middleware(bot: TeleBot, logger):
    """Middleware для автоматической проверки безопасности"""
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(message_or_call: Message | CallbackQuery, *args, **kwargs):
            try:
                # Получаем user_id в зависимости от типа
                if isinstance(message_or_call, Message):
                    user_id = message_or_call.from_user.id
                    chat_id = message_or_call.chat.id
                    action_type = "message"
                elif isinstance(message_or_call, CallbackQuery):
                    user_id = message_or_call.from_user.id
                    chat_id = message_or_call.message.chat.id
                    action_type = "callback"
                else:
                    # Если это не Message и не CallbackQuery, пропускаем
                    return func(message_or_call, *args, **kwargs)
                
                # Проверка безопасности
                security_ok, error_msg = check_user_security(user_id, action_type)
                if not security_ok:  
                    # Логируем подозрительную активность
                    security_manager.record_suspicious_activity(user_id, f"blocked_{action_type}")
                    
                    if isinstance(message_or_call, Message):
                        bot.send_message(chat_id, f"🚫 {error_msg}")
                    elif isinstance(message_or_call, CallbackQuery):
                        bot.answer_callback_query(message_or_call.id, f"🚫 {error_msg}")
                    
                    # Логируем блокировку
                    log_user_action(logger, user_id, f"BLOCKED_{action_type}", f"Reason: {error_msg}")
                    return
                
                # Если все проверки пройдены, выполняем функцию
                return func(message_or_call, *args, **kwargs)
                
            except Exception as e:
                log_error(logger, e, f"Security middleware error for {func.__name__}")
                # В случае ошибки в middleware, все равно выполняем функцию
                return func(message_or_call, *args, **kwargs)
        
        return wrapper
    return decorator

def admin_only_middleware(bot: TeleBot, logger):
    """Middleware для проверки прав администратора"""
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(message_or_call: Message | CallbackQuery, *args, **kwargs):
            try:
                # Получаем user_id
                if isinstance(message_or_call, Message):
                    user_id = message_or_call.from_user.id
                    chat_id = message_or_call.chat.id
                elif isinstance(message_or_call, CallbackQuery):
                    user_id = message_or_call.from_user.id
                    chat_id = message_or_call.message.chat.id
                else:
                    return func(message_or_call, *args, **kwargs)
                
                # Проверяем права администратора
                if not is_admin(user_id):
                    error_msg = "У вас нет прав для выполнения этого действия"
                    if isinstance(message_or_call, Message):
                        bot.send_message(chat_id, f"🚫 {error_msg}")
                    elif isinstance(message_or_call, CallbackQuery):
                        bot.answer_callback_query(message_or_call.id, f"🚫 {error_msg}")
                    
                    log_user_action(logger, user_id, "UNAUTHORIZED_ADMIN_ACCESS", f"Function: {func.__name__}")
                    return
                
                return func(message_or_call, *args, **kwargs)
                
            except Exception as e:
                log_error(logger, e, f"Admin middleware error for {func.__name__}")
                return func(message_or_call, *args, **kwargs)
        
        return wrapper
    return decorator

def input_validation_middleware(bot: TeleBot, logger, validation_type: str = "message"):
    """Middleware для валидации входных данных"""
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(message: Message, *args, **kwargs):
            try:
                if not isinstance(message, Message):
                    return func(message, *args, **kwargs)
                
                # Валидация текста сообщения
                if hasattr(message, 'text') and message.text:
                    from utils.security import validate_user_input
                    is_valid, error_msg = validate_user_input(message.text, validation_type)
                    if not is_valid:
                        bot.send_message(message.chat.id, f"❌ {error_msg}")
                        log_user_action(logger, message.from_user.id, "INVALID_INPUT", f"Type: {validation_type}, Error: {error_msg}")
                        return
                
                return func(message, *args, **kwargs)
                
            except Exception as e:
                log_error(logger, e, f"Input validation middleware error for {func.__name__}")
                return func(message, *args, **kwargs)
        
        return wrapper
    return decorator

def rate_limit_middleware(bot: TeleBot, logger, custom_limit: int = None):
    """Middleware для rate limiting с кастомным лимитом"""
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(message_or_call: Message | CallbackQuery, *args, **kwargs):
            try:
                # Получаем user_id
                if isinstance(message_or_call, Message):
                    user_id = message_or_call.from_user.id
                    chat_id = message_or_call.chat.id
                elif isinstance(message_or_call, CallbackQuery):
                    user_id = message_or_call.from_user.id
                    chat_id = message_or_call.message.chat.id
                else:
                    return func(message_or_call, *args, **kwargs)
                
                # Проверяем rate limit
                if custom_limit:
                    # Временно изменяем лимит для этой функции
                    original_limit = security_manager.rate_limit_data.get(user_id, [])
                    if len(original_limit) >= custom_limit:
                        error_msg = f"Слишком много запросов. Лимит: {custom_limit} в минуту"
                        if isinstance(message_or_call, Message):
                            bot.send_message(chat_id, f"🚫 {error_msg}")
                        elif isinstance(message_or_call, CallbackQuery):
                            bot.answer_callback_query(message_or_call.id, f"🚫 {error_msg}")
                        return
                
                return func(message_or_call, *args, **kwargs)
                
            except Exception as e:
                log_error(logger, e, f"Rate limit middleware error for {func.__name__}")
                return func(message_or_call, *args, **kwargs)
        
        return wrapper
    return decorator

def log_activity_middleware(bot: TeleBot, logger, activity_name: str = None):
    """Middleware для логирования активности пользователей"""
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(message_or_call: Message | CallbackQuery, *args, **kwargs):
            try:
                # Получаем информацию о пользователе
                if isinstance(message_or_call, Message):
                    user_id = message_or_call.from_user.id
                    username = message_or_call.from_user.username
                    text = message_or_call.text
                elif isinstance(message_or_call, CallbackQuery):
                    user_id = message_or_call.from_user.id
                    username = message_or_call.from_user.username
                    text = message_or_call.data
                else:
                    return func(message_or_call, *args, **kwargs)
                
                # Логируем активность
                activity = activity_name or func.__name__
                log_user_action(logger, user_id, activity, f"Username: {username}, Input: {text}")
                
                return func(message_or_call, *args, **kwargs)
                
            except Exception as e:
                log_error(logger, e, f"Log activity middleware error for {func.__name__}")
                return func(message_or_call, *args, **kwargs)
        
        return wrapper
    return decorator

def is_admin(user_id):
    return str(user_id) == str(ADMIN_ID) 