from utils.logger import setup_logger
from functools import wraps


def error_handler(send_user_message=True):
    """
    Декоратор для централизованной обработки ошибок и логирования.
    Если send_user_message=True, при ошибке отправляет пользователю стандартное сообщение.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger = setup_logger('error_handler')
                # Пытаемся найти bot и message среди аргументов
                bot = None
                message = None
                for arg in args:
                    # telebot.TeleBot обычно имеет метод send_message
                    if hasattr(arg, 'send_message'):
                        bot = arg
                    # message обычно имеет chat и from_user
                    if hasattr(arg, 'chat') and hasattr(arg, 'from_user'):
                        message = arg   
                # Логируем ошибку
                logger.error(f"Error in {func.__name__}: {e}", exc_info=True)
                # Отправляем сообщение пользователю, если возможно
                if send_user_message and bot and message:
                    try:
                        bot.send_message(message.chat.id, "⚠️ Произошла ошибка. Попробуйте позже.")
                    except Exception as send_err:
                        logger.error(f"Failed to send error message to user: {send_err}")
        return wrapper
    return decorator 