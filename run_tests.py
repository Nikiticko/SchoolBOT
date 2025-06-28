#!/usr/bin/env python3
"""
Скрипт для запуска всех тестов проекта
"""

import unittest
import sys
import os

def run_tests():
    """Запускает все тесты проекта"""
    # Добавляем корневую директорию в путь
    project_root = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, project_root)
    
    # Находим все тестовые файлы
    test_loader = unittest.TestLoader()
    test_suite = unittest.TestSuite()
    
    # Добавляем тесты из папки tests
    tests_dir = os.path.join(project_root, 'tests')
    if os.path.exists(tests_dir):
        test_suite.addTests(test_loader.discover(tests_dir, pattern='test_*.py'))
    
    # Запускаем тесты
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Возвращаем код выхода
    return 0 if result.wasSuccessful() else 1

if __name__ == '__main__':
    print("🧪 Запуск тестов проекта...")
    print("=" * 50)
    
    exit_code = run_tests()
    
    print("=" * 50)
    if exit_code == 0:
        print("✅ Все тесты прошли успешно!")
    else:
        print("❌ Некоторые тесты не прошли!")
    
    sys.exit(exit_code) 