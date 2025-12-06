"""Test the payment report functionality"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vk_bot.handlers.payment_report import parse_payment_report_query

# Test parsing
test_cases = [
    "отчет по оплатам Назрань ноябрь",
    "отчет по оплатам все ноябрь",
    "отчет по оплатам Назрань",
    "отчет по оплатам Москва декабрь",
]

print("Тестирование парсинга запросов:\n")
for test in test_cases:
    result = parse_payment_report_query(test)
    print(f"Запрос: '{test}'")
    print(f"Результат: {result}")
    print()
