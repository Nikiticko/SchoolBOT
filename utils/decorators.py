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

def ensure_text_message(func):
    """
    Декоратор для проверки, что сообщение текстовое.
    Если нет — отправляет пользователю подсказку и не вызывает обработчик.
    """
    @wraps(func)
    def wrapper(message, *args, **kwargs):
        if not hasattr(message, 'text') or message.text is None:
            # Пытаемся получить bot из аргументов или message
            bot = getattr(message, 'bot', None)
            if not bot:
                for arg in args:
                    if hasattr(arg, 'send_message'):
                        bot = arg
                        break
            if bot:
                bot.send_message(message.chat.id, "Пожалуйста, введите текстовое сообщение.")
            return
        return func(message, *args, **kwargs)
    return wrapper 

def ensure_stage(get_stage_func, expected_stage, error_message="Вы не на нужном этапе. Начните заново."):
    """
    Декоратор для проверки, что пользователь находится на нужном этапе.
    get_stage_func(message) -> str — функция, возвращающая текущий этап пользователя
    expected_stage — ожидаемый этап
    error_message — сообщение пользователю, если этап не совпадает
    """
    def decorator(func):
        @wraps(func)
        def wrapper(message, *args, **kwargs):
            stage = get_stage_func(message)
            if stage != expected_stage:
                bot = getattr(message, 'bot', None)
                if not bot:
                    for arg in args:
                        if hasattr(arg, 'send_message'):
                            bot = arg
                            break
                if bot:
                    bot.send_message(message.chat.id, error_message)
                return
            return func(message, *args, **kwargs)
        return wrapper
    return decorator 