import threading
import time
from datetime import datetime, timedelta
from telebot import types
from data.db import (
    get_lessons_completed_after_time, 
    mark_review_request_sent,
    has_user_reviewed_application,
    get_application_by_id,
    get_upcoming_lessons,
    mark_reminder_sent,
    format_date_for_display
)
from utils.logger import setup_logger

logger = setup_logger('review_monitor')

class ReviewRequestMonitor:
    """Монитор для отправки запросов на оценку пройденных занятий"""
    
    def __init__(self, bot):
        self.bot = bot
        self.is_running = False
        self.monitor_thread = None
        self.check_interval = 300  # 5 минут
        self.delay_after_lesson = 0.5  # 30 минут после урока
        
    def start(self):
        """Запускает монитор в отдельном потоке"""
        if self.is_running:
            logger.warning("Review monitor is already running")
            return
            
        self.is_running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("Review request monitor started")
        
    def stop(self):
        """Останавливает монитор"""
        self.is_running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("Review request monitor stopped")
        
    def _monitor_loop(self):
        """Основной цикл мониторинга"""
        while self.is_running:
            try:
                self._check_and_send_review_requests()
                time.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Error in review monitor loop: {e}")
                time.sleep(60)  # Ждем минуту при ошибке
                
    def _check_and_send_review_requests(self):
        """Проверяет и отправляет запросы на оценку"""
        try:
            # Получаем уроки, завершенные более 30 минут назад
            completed_lessons = get_lessons_completed_after_time(self.delay_after_lesson)
            
            if not completed_lessons:
                return
                
            logger.info(f"Found {len(completed_lessons)} lessons eligible for review requests")
            
            for lesson in completed_lessons:
                app_id, tg_id, course, lesson_date, lesson_link = lesson
                
                try:
                    self._send_review_request(app_id, tg_id, course)
                    # Отмечаем, что запрос отправлен
                    try:
                        mark_review_request_sent(app_id)
                    except Exception as e:
                        logger.error(f"Failed to mark review request sent for application {app_id}: {e}")
                    logger.info(f"Review request sent for application {app_id}")
                    
                except Exception as e:
                    logger.error(f"Failed to send review request for application {app_id}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error checking review requests: {e}")
            
    def _send_review_request(self, app_id, tg_id, course):
        """Отправляет запрос на оценку пользователю"""
        try:
            # Проверяем, не оставил ли уже пользователь отзыв
            if has_user_reviewed_application(app_id, tg_id):
                logger.info(f"User {tg_id} already reviewed application {app_id}")
                return
                
            # Формируем сообщение
            msg = (
                f"🎉 Спасибо за участие в уроке!\n\n"
                f"📘 Курс: {course}\n\n"
                f"Пожалуйста, поделитесь своими впечатлениями о занятии. "
                f"Ваш отзыв поможет нам стать лучше! 🌟"
            )
            
            # Создаем клавиатуру
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton("⭐ Оставить отзыв", callback_data=f"start_review:{app_id}"),
                types.InlineKeyboardButton("❌ Пропустить", callback_data="skip_review")
            )
            
            # Отправляем сообщение
            self.bot.send_message(tg_id, msg, reply_markup=markup)
            
        except Exception as e:
            logger.error(f"Error sending review request to user {tg_id}: {e}")
            raise
            
    def send_immediate_review_request(self, app_id):
        """Отправляет запрос на оценку немедленно (для тестирования или ручного запуска)"""
        try:
            # Получаем данные заявки
            app_data = get_application_by_id(app_id)
            if not app_data:
                logger.error(f"Application {app_id} not found")
                return False
                
            tg_id = app_data[1]
            course = app_data[6]
            
            # Проверяем, не оставил ли уже пользователь отзыв
            if has_user_reviewed_application(app_id, tg_id):
                logger.info(f"User {tg_id} already reviewed application {app_id}")
                return False
                
            # Отправляем запрос
            self._send_review_request(app_id, tg_id, course)
            
            # Отмечаем, что запрос отправлен
            try:
                mark_review_request_sent(app_id)
            except Exception as e:
                logger.error(f"Failed to mark review request sent for application {app_id}: {e}")
            logger.info(f"Immediate review request sent for application {app_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending immediate review request for application {app_id}: {e}")
            return False
            
    def get_stats(self):
        """Возвращает статистику монитора"""
        try:
            from data.db import get_database_stats
            stats = get_database_stats()
            
            # Добавляем информацию о мониторе
            stats.update({
                'monitor_running': self.is_running,
                'check_interval_seconds': self.check_interval,
                'delay_after_lesson_hours': self.delay_after_lesson
            })
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting monitor stats: {e}")
            return {}

# Глобальный экземпляр монитора
review_monitor = None

def init_review_monitor(bot):
    """Инициализирует и запускает монитор запросов на оценку"""
    global review_monitor
    review_monitor = ReviewRequestMonitor(bot)
    review_monitor.start()
    return review_monitor

def get_review_monitor():
    """Возвращает глобальный экземпляр монитора"""
    return review_monitor

def stop_review_monitor():
    """Останавливает монитор запросов на оценку"""
    global review_monitor
    if review_monitor:
        review_monitor.stop()
        review_monitor = None

class LessonReminderMonitor:
    """Монитор для отправки напоминаний о предстоящих уроках за 30 минут"""
    def __init__(self, bot):
        self.bot = bot
        self.is_running = False
        self.monitor_thread = None
        self.check_interval = 120  # Проверять каждые 2 минуты
        self.reminder_minutes = 30

    def start(self):
        if self.is_running:
            logger.warning("Lesson reminder monitor is already running")
            return
        self.is_running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("Lesson reminder monitor started")

    def stop(self):
        self.is_running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("Lesson reminder monitor stopped")

    def _monitor_loop(self):
        while self.is_running:
            try:
                self._check_and_send_reminders()
                time.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Error in lesson reminder monitor loop: {e}")
                time.sleep(60)

    def _check_and_send_reminders(self):
        try:
            lessons = get_upcoming_lessons(self.reminder_minutes)
            if not lessons:
                return
            logger.info(f"Found {len(lessons)} lessons for reminders")
            for lesson in lessons:
                app_id, tg_id, parent_name, student_name, age, contact, course, lesson_date, lesson_link, status, created_at, reminder_sent = lesson
                try:
                    formatted_date = format_date_for_display(lesson_date)
                    msg = (
                        f"⏰ Напоминание! Ваш урок начнётся через 30 минут или меньше.\n"
                        f"📅 Дата: {formatted_date}\n"
                        f"📘 Курс: {course}\n"
                        f"🔗 Ссылка: {lesson_link}"
                    )
                    self.bot.send_message(tg_id, msg)
                    try:
                        mark_reminder_sent(app_id)
                    except Exception as e:
                        logger.error(f"Failed to mark reminder sent for application {app_id}: {e}")
                    logger.info(f"[REMINDER] Sent to user {tg_id} for lesson {app_id}")
                except Exception as e:
                    logger.error(f"[REMINDER] Failed to send to {tg_id}: {e}")
        except Exception as e:
            logger.error(f"Error checking reminders: {e}")

# Глобальный экземпляр монитора напоминаний
lesson_reminder_monitor = None

def init_lesson_reminder_monitor(bot):
    global lesson_reminder_monitor
    lesson_reminder_monitor = LessonReminderMonitor(bot)
    lesson_reminder_monitor.start()
    return lesson_reminder_monitor

def stop_lesson_reminder_monitor():
    global lesson_reminder_monitor
    if lesson_reminder_monitor:
        lesson_reminder_monitor.stop()
        lesson_reminder_monitor = None
