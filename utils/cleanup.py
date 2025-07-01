"""
Модуль автоматической очистки временных файлов
Безопасно удаляет только временные файлы, не влияя на работу бота
"""

import os
import glob
import time
import threading
from datetime import datetime, timedelta
from utils.logger import setup_logger

class AutoCleanup:
    """
    Автоматическая очистка временных файлов
    Удаляет только безопасные файлы старше 24 часов
    """
    
    def __init__(self):
        self.logger = setup_logger('auto_cleanup')
        self.safe_patterns = [
            "*.xlsx",           # Excel файлы экспорта
            "*.log.*",          # Старые логи (не текущий bot.log)
            "state/*.tmp",      # Временные файлы состояния
        ]
        self.max_age_hours = 24  # Удалять файлы старше 24 часов
        self.critical_files = [
            "database.db",      # Основная БД
            "state.json",       # Текущее состояние
            "bot.log",          # Текущий лог
            "config.env",       # Конфигурация
            "requirements.txt", # Зависимости
        ]
        
    def cleanup_safe_files(self):
        """Очищает только безопасные временные файлы"""
        try:
            cleaned_count = 0
            total_size = 0
            
            for pattern in self.safe_patterns:
                files = glob.glob(pattern)
                for file_path in files:
                    if self._is_safe_to_delete(file_path):
                        try:
                            file_size = os.path.getsize(file_path)
                            os.remove(file_path)
                            cleaned_count += 1
                            total_size += file_size
                            self.logger.info(f"🧹 Auto-cleanup: removed {file_path}")
                        except Exception as e:
                            self.logger.error(f"❌ Failed to remove {file_path}: {e}")
            
            if cleaned_count > 0:
                size_mb = total_size / (1024 * 1024)
                self.logger.info(f"✅ Auto-cleanup completed: {cleaned_count} files removed, {size_mb:.2f} MB freed")
            else:
                self.logger.info("✅ Auto-cleanup: no files to remove")
                
        except Exception as e:
            self.logger.error(f"❌ Auto-cleanup error: {e}")
    
    def _is_safe_to_delete(self, file_path):
        """Проверяет, безопасно ли удалять файл"""
        try:
            filename = os.path.basename(file_path)
            
            # Не удаляем критические файлы
            if any(critical in filename for critical in self.critical_files):
                return False
            
            # Проверяем возраст файла
            file_age = time.time() - os.path.getmtime(file_path)
            max_age_seconds = self.max_age_hours * 3600
            
            if file_age < max_age_seconds:
                return False
                
            # Дополнительная проверка: не удаляем файлы, которые используются
            if self._is_file_in_use(file_path):
                return False
                
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking file {file_path}: {e}")
            return False
    
    def _is_file_in_use(self, file_path):
        """Проверяет, используется ли файл в данный момент"""
        try:
            # Пытаемся открыть файл на запись (это покажет, используется ли он)
            with open(file_path, 'a'):
                pass
            return False
        except (PermissionError, OSError):
            # Файл заблокирован или используется
            return True
    
    def get_cleanup_stats(self):
        """Возвращает статистику файлов для очистки"""
        try:
            stats = {
                'total_files': 0,
                'total_size': 0,
                'files_to_clean': 0,
                'size_to_free': 0
            }
            
            for pattern in self.safe_patterns:
                files = glob.glob(pattern)
                for file_path in files:
                    try:
                        file_size = os.path.getsize(file_path)
                        stats['total_files'] += 1
                        stats['total_size'] += file_size
                        
                        if self._is_safe_to_delete(file_path):
                            stats['files_to_clean'] += 1
                            stats['size_to_free'] += file_size
                    except:
                        continue
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting cleanup stats: {e}")
            return stats
    
    def start_periodic_cleanup(self, interval_hours=6):
        """Запускает периодическую очистку"""
        def cleanup_loop():
            self.logger.info(f"🔄 Auto-cleanup started (every {interval_hours} hours)")
            while True:
                try:
                    time.sleep(interval_hours * 3600)
                    self.cleanup_safe_files()
                except Exception as e:
                    self.logger.error(f"Error in cleanup loop: {e}")
                    time.sleep(3600)  # Ждем час при ошибке
        
        cleanup_thread = threading.Thread(target=cleanup_loop, daemon=True)
        cleanup_thread.start()
        self.logger.info(f"✅ Auto-cleanup thread started successfully")
    
    def manual_cleanup(self):
        """Ручная очистка (для тестирования)"""
        self.logger.info("🧹 Manual cleanup started")
        self.cleanup_safe_files()

# Глобальный экземпляр для использования в других модулях
auto_cleanup = AutoCleanup() 