"""
Менеджер состояний для безопасного хранения данных пользователей
"""

import json
import os
import threading
import time
from typing import Dict, Any, Optional, Set
from datetime import datetime, timedelta
from utils.logger import setup_logger

class StateManager:
    """
    Безопасный менеджер состояний с персистентностью и thread-safety
    """
    
    def __init__(self, storage_file: str = "state/state.json", auto_save_interval: int = 300):
        self.storage_file = storage_file
        self.auto_save_interval = auto_save_interval
        self.logger = setup_logger('state_manager')
        
        # Thread-safe хранилище
        self._lock = threading.RLock()
        self._state = {
            "user_data": {},           # Временные данные для FSM регистрации
            "chat_contact_map": {},    # Telegram ID ↔ Контакт
            "pending": {},             # Ожидающие назначения уведомления
            "writing_ids": set(),      # ID заявок в обработке
            "rate_limit_data": {},     # Данные rate limiting
            "banned_users": set(),     # Забаненные пользователи
            "suspicious_activities": {} # Подозрительная активность
        }
        
        # Автосохранение
        self._last_save = time.time()
        self._save_thread = None
        self._running = False
        
        # Загружаем состояние
        self._load_state()
        self._start_auto_save()
    
    def _load_state(self):
        """Загружает состояние из файла"""
        try:
            if os.path.exists(self.storage_file):
                with open(self.storage_file, 'r', encoding='utf-8') as f:
                    loaded_state = json.load(f)
                    
                # Обновляем состояние, сохраняя структуру
                for key, value in loaded_state.items():
                    if key in self._state:
                        if key in ["writing_ids", "banned_users"]:
                            # Преобразуем списки обратно в множества
                            self._state[key] = set(value)
                        else:
                            self._state[key] = value
                
                self.logger.info(f"✅ Состояние загружено из {self.storage_file}")
            else:
                self.logger.info("📝 Создано новое состояние")
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка загрузки состояния: {e}")
    
    def _save_state(self):
        """Сохраняет состояние в файл"""
        try:
            # Создаем директорию если не существует
            os.makedirs(os.path.dirname(self.storage_file), exist_ok=True)
            
            # Подготавливаем данные для сохранения
            save_data = {}
            with self._lock:
                for key, value in self._state.items():
                    if isinstance(value, set):
                        # Преобразуем множества в списки для JSON
                        save_data[key] = list(value)
                    else:
                        save_data[key] = value
            
            # Сохраняем с временным файлом для атомарности
            temp_file = f"{self.storage_file}.tmp"
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
            
            # Атомарно переименовываем
            os.replace(temp_file, self.storage_file)
            self._last_save = time.time()
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка сохранения состояния: {e}")
    
    def _start_auto_save(self):
        """Запускает автоматическое сохранение"""
        self._running = True
        self._save_thread = threading.Thread(target=self._auto_save_loop, daemon=True)
        self._save_thread.start()
    
    def _auto_save_loop(self):
        """Цикл автоматического сохранения"""
        while self._running:
            time.sleep(60)  # Проверяем каждую минуту
            if time.time() - self._last_save > self.auto_save_interval:
                self._save_state()
    
    def stop(self):
        """Останавливает менеджер состояний"""
        self._running = False
        if self._save_thread:
            self._save_thread.join(timeout=5)
        self._save_state()
        self.logger.info("🛑 Менеджер состояний остановлен")
    
    # Методы для работы с user_data
    def get_user_data(self, user_id: int) -> Dict[str, Any]:
        """Получает данные пользователя"""
        with self._lock:
            return self._state["user_data"].get(str(user_id), {})
    
    def set_user_data(self, user_id: int, data: Dict[str, Any]):
        """Устанавливает данные пользователя"""
        with self._lock:
            self._state["user_data"][str(user_id)] = data
    
    def update_user_data(self, user_id: int, **kwargs):
        """Обновляет данные пользователя"""
        with self._lock:
            user_id_str = str(user_id)
            if user_id_str not in self._state["user_data"]:
                self._state["user_data"][user_id_str] = {}
            self._state["user_data"][user_id_str].update(kwargs)
    
    def clear_user_data(self, user_id: int):
        """Очищает данные пользователя"""
        with self._lock:
            self._state["user_data"].pop(str(user_id), None)
    
    # Методы для работы с chat_contact_map
    def get_chat_contact(self, chat_id: int) -> Optional[str]:
        """Получает контакт для чата"""
        with self._lock:
            return self._state["chat_contact_map"].get(str(chat_id))
    
    def set_chat_contact(self, chat_id: int, contact: str):
        """Устанавливает контакт для чата"""
        with self._lock:
            self._state["chat_contact_map"][str(chat_id)] = contact
    
    def remove_chat_contact(self, chat_id: int):
        """Удаляет контакт для чата"""
        with self._lock:
            self._state["chat_contact_map"].pop(str(chat_id), None)
    
    # Методы для работы с pending
    def add_pending(self, user_id: int, data: Dict[str, Any]):
        """Добавляет ожидающее уведомление"""
        with self._lock:
            self._state["pending"][str(user_id)] = data
    
    def get_pending(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получает ожидающее уведомление"""
        with self._lock:
            return self._state["pending"].get(str(user_id))
    
    def remove_pending(self, user_id: int):
        """Удаляет ожидающее уведомление"""
        with self._lock:
            self._state["pending"].pop(str(user_id), None)
    
    def get_all_pending(self) -> Dict[str, Dict[str, Any]]:
        """Получает все ожидающие уведомления"""
        with self._lock:
            return self._state["pending"].copy()
    
    # Методы для работы с writing_ids
    def add_writing_id(self, app_id: int):
        """Добавляет ID заявки в обработку"""
        with self._lock:
            self._state["writing_ids"].add(app_id)
    
    def remove_writing_id(self, app_id: int):
        """Удаляет ID заявки из обработки"""
        with self._lock:
            self._state["writing_ids"].discard(app_id)
    
    def is_writing_id(self, app_id: int) -> bool:
        """Проверяет, обрабатывается ли заявка"""
        with self._lock:
            return app_id in self._state["writing_ids"]
    
    # Методы для работы с rate_limit_data
    def get_rate_limit_data(self, user_id: int) -> list:
        """Получает данные rate limit для пользователя"""
        with self._lock:
            return self._state["rate_limit_data"].get(str(user_id), [])
    
    def set_rate_limit_data(self, user_id: int, timestamps: list):
        """Устанавливает данные rate limit для пользователя"""
        with self._lock:
            self._state["rate_limit_data"][str(user_id)] = timestamps
    
    def clear_rate_limit_data(self, user_id: int):
        """Очищает данные rate limit для пользователя"""
        with self._lock:
            self._state["rate_limit_data"].pop(str(user_id), None)
    
    # Методы для работы с banned_users
    def add_banned_user(self, user_id: int):
        """Добавляет пользователя в бан"""
        with self._lock:
            self._state["banned_users"].add(user_id)
    
    def remove_banned_user(self, user_id: int):
        """Удаляет пользователя из бана"""
        with self._lock:
            self._state["banned_users"].discard(user_id)
    
    def is_user_banned(self, user_id: int) -> bool:
        """Проверяет, забанен ли пользователь"""
        with self._lock:
            return user_id in self._state["banned_users"]
    
    def get_banned_users(self) -> Set[int]:
        """Получает всех забаненных пользователей"""
        with self._lock:
            return self._state["banned_users"].copy()
    
    # Методы для работы с suspicious_activities
    def get_suspicious_count(self, user_id: int) -> int:
        """Получает количество подозрительных действий пользователя"""
        with self._lock:
            return self._state["suspicious_activities"].get(str(user_id), 0)
    
    def increment_suspicious_count(self, user_id: int):
        """Увеличивает счетчик подозрительных действий"""
        with self._lock:
            user_id_str = str(user_id)
            current = self._state["suspicious_activities"].get(user_id_str, 0)
            self._state["suspicious_activities"][user_id_str] = current + 1
    
    def clear_suspicious_count(self, user_id: int):
        """Очищает счетчик подозрительных действий"""
        with self._lock:
            self._state["suspicious_activities"].pop(str(user_id), None)
    
    # Общие методы
    def get_stats(self) -> Dict[str, Any]:
        """Получает статистику состояния"""
        with self._lock:
            return {
                "user_data_count": len(self._state["user_data"]),
                "chat_contact_count": len(self._state["chat_contact_map"]),
                "pending_count": len(self._state["pending"]),
                "writing_ids_count": len(self._state["writing_ids"]),
                "banned_users_count": len(self._state["banned_users"]),
                "suspicious_activities_count": len(self._state["suspicious_activities"]),
                "last_save": datetime.fromtimestamp(self._last_save).isoformat()
            }
    
    def clear_all(self):
        """Очищает все данные (только для тестов!)"""
        with self._lock:
            self._state = {
                "user_data": {},
                "chat_contact_map": {},
                "pending": {},
                "writing_ids": set(),
                "rate_limit_data": {},
                "banned_users": set(),
                "suspicious_activities": {}
            }
        self._save_state()

# Глобальный экземпляр менеджера состояний
state_manager = StateManager()

# Функции для обратной совместимости
def get_user_data(user_id: int) -> Dict[str, Any]:
    """Получает данные пользователя (обратная совместимость)"""
    return state_manager.get_user_data(user_id)

def set_user_data(user_id: int, data: Dict[str, Any]):
    """Устанавливает данные пользователя (обратная совместимость)"""
    state_manager.set_user_data(user_id, data)

def get_pending() -> Dict[str, Dict[str, Any]]:
    """Получает все ожидающие уведомления (обратная совместимость)"""
    return state_manager.get_all_pending()

def get_writing_ids() -> Set[int]:
    """Получает ID заявок в обработке (обратная совместимость)"""
    with state_manager._lock:
        return state_manager._state["writing_ids"].copy() 