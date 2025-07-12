#!/usr/bin/env python3
"""
Утилита для проверки целостности базы данных
Использование: python utils/db_check.py
"""

import sys
import os

# Добавляем корневую директорию в путь
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.db import check_database_integrity, get_database_stats

def main():
    """Главная функция"""
    print("🔍 ПРОВЕРКА ЦЕЛОСТНОСТИ БАЗЫ ДАННЫХ")
    print("=" * 50)
    
    try:
        # Проверяем целостность
        is_ok, error_msg = check_database_integrity()
        
        if is_ok:
            print("✅ Целостность БД в порядке")
            
            # Показываем статистику
            try:
                stats = get_database_stats()
                print("\n📊 Статистика БД:")
                for key, value in stats.items():
                    # Переводим ключи на русский
                    key_names = {
                        'pending_applications': 'Ожидающие заявки',
                        'assigned_applications': 'Назначенные заявки',
                        'archived_applications': 'Архивные заявки',
                        'active_courses': 'Активные курсы',
                        'reviews_count': 'Количество отзывов',
                        'open_contacts': 'Открытые обращения'
                    }
                    display_name = key_names.get(key, key)
                    print(f"   {display_name}: {value}")
            except Exception as e:
                print(f"⚠️ Не удалось получить статистику: {e}")
            
            print("\n✅ Проверка завершена успешно")
            sys.exit(0)
        else:
            print(f"❌ БД повреждена: {error_msg}")
            print("\n🔧 Рекомендации:")
            print("1. Создайте резервную копию поврежденной БД")
            print("2. Попробуйте восстановить из резервной копии")
            print("3. Если нет резервной копии, создайте новую БД")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 