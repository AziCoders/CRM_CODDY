"""Тестовый скрипт для проверки парсинга дат"""
import sys
import os
from pathlib import Path

# Добавляем корневую директорию в путь
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from bot.services.reminder_service import ReminderService


def test_parse_date_field():
    """Тестирует функцию парсинга дат"""
    print("=" * 60)
    print("Тестирование функции _parse_date_field()")
    print("=" * 60)
    
    reminder_service = ReminderService()
    
    # Тестовые случаи
    test_cases = [
        ("25.11.2025", True),  # Обычная дата
        ("25.11.2025 ", True),  # С пробелом в конце
        (" 25.11.2025", True),  # С пробелом в начале
        ("1.1.2025", True),     # Однозначные числа
        ("31.12.2024", True),   # Конец года
        ("01.01.2025", True),   # С нулями
        ("invalid", False),     # Невалидная дата
        ("", False),            # Пустая строка
        ("25/11/2025", False),  # Неправильный формат
        ("2025.11.25", False),  # Неправильный порядок
    ]
    
    print("\n📋 Тестовые случаи:\n")
    
    passed = 0
    failed = 0
    
    for date_str, should_parse in test_cases:
        result = reminder_service._parse_date_field(date_str)
        is_parsed = result is not None
        
        if is_parsed == should_parse:
            status = "✅"
            passed += 1
        else:
            status = "❌"
            failed += 1
        
        print(f"{status} '{date_str}' -> {result} (ожидалось: {'парсинг' if should_parse else 'ошибка'})")
    
    print("\n" + "=" * 60)
    print(f"Результаты: ✅ {passed} пройдено, ❌ {failed} провалено")
    print("=" * 60)


if __name__ == "__main__":
    test_parse_date_field()
