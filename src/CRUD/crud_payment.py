"""
МОДУЛЬ: crud_payment.py
=======================

Назначение:
-----------
Управление таблицей оплат в Notion для конкретного города.

Файл реализует функциональность добавления новых месяцев,
добавления учеников в таблицу оплат, отметки статуса оплаты
(«Оплатил», «Не оплатил», «Написали», «Отсрочка», "Не были записаны"), а также
автоматическую синхронизацию данных с локальным файлом
`payments.json`.

После любого изменения (добавление месяца, ученика или изменения статуса оплаты)
модуль автоматически вызывает пересборку JSON-файла через класс
`NotionPaymentsFetcher` из `src/sync_data/payments.py`.
"""

import os
import json
from datetime import date
from typing import Optional

from src.config import ROOT_DIR, get_notion_client
from src.sync_data.payments import NotionPaymentsFetcher


class NotionPaymentUpdater:
    """
    Класс: NotionPaymentUpdater
    ===========================
    """

    def __init__(self, city_name: str):
        self.city_name = city_name.capitalize()
        # Use shared client
        self.notion = get_notion_client()

        # === ID базы оплат ===
        self.database_id = os.getenv(f"{self.city_name.upper()}_PAYMENT_ID")
        if not self.database_id:
            raise ValueError(f"❌ Не найден ключ {self.city_name.upper()}_PAYMENT_ID в .env")

        # === Путь к students.json ===
        self.root_dir = ROOT_DIR
        self.students_path = self.root_dir / f"data/{self.city_name}/students.json"

        # DEBUG PRINT
        print(f"[DEBUG] NotionPaymentUpdater initialized.")
        print(f"[DEBUG] ROOT_DIR: {self.root_dir}")
        print(f"[DEBUG] students_path: {self.students_path}")

    # ----------------------------------------------------------------
    # === ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ===

    # ----------------------------------------------------------------
    # === ОСНОВНОЙ ФУНКЦИОНАЛ ===
    # ----------------------------------------------------------------
    async def add_month_column(self, month_name: str):
        """
        Добавляет новый столбец (месяц) в таблицу оплат и обновляет JSON.
        """
        # 1. Проверяем, есть ли уже такой месяц в схеме базы
        db_info = await self.notion.databases.retrieve(database_id=self.database_id)
        props = db_info.get("properties", {})

        if month_name in props:
            print(f"⚠️ Столбец месяца '{month_name}' уже существует — добавление пропущено.")
            return

        # 2. Если нет — создаём новый select-столбец
        options = [
            {"name": "Оплатил", "color": "green"},
            {"name": "Не оплатил", "color": "red"},
            {"name": "Написали", "color": "blue"},
            {"name": "Отсрочка", "color": "yellow"},
            {"name": "Не были записаны", "color": "gray"},
        ]

        await self.notion.databases.update(
            database_id=self.database_id,
            properties={
                month_name: {
                    "type": "select",
                    "select": {"options": options},
                }
            },
        )
        print(f"✅ Добавлен новый столбец: {month_name}")


    def load_students(self) -> list:
        """Загружает всех учеников из файла students.json."""
        if not self.students_path.exists():
            raise FileNotFoundError(f"❌ Файл {self.students_path} не найден")

        with open(self.students_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        students = []
        for group in data.values():
            for student in group.get("students", []):
                students.append(student)
        print(f"📘 Загружено {len(students)} учеников из students.json")
        return students

    async def add_student_to_payments(self, student: dict, payment_date: Optional[str] = None):
        """
        Добавляет одного ученика в таблицу оплат и обновляет JSON.
        """
        fio = student["ФИО"].strip()
        phone = student.get("Номер родителя", "")
        comment = ""
        student_url = student.get("student_url")

        # Проверяем только ФИО
        response = await self.notion.databases.query(
            database_id=self.database_id,
            filter={"property": "ФИО", "rich_text": {"equals": fio}}
        )

        # Если ученик найден — не добавляем дубль
        if response["results"]:
            print(f"⚠️ Ученик '{fio}' уже есть в таблице оплат — пропуск.")
            return

        # Если дата не передана вручную — используем сегодняшнее число
        if not payment_date:
            today = date.today().day
            payment_date = f"{today} числа"

        # Создаём запись в таблице оплат
        await self.notion.pages.create(
            parent={"database_id": self.database_id},
            properties={
                "Дата оплаты": {
                    "title": [{"type": "text", "text": {"content": payment_date}}],
                },
                "ФИО": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {"content": fio, "link": {"url": student_url}},
                        }
                    ]
                },
                "Phone": {"phone_number": phone or None},
                "Комментарий": {
                    "rich_text": [{"type": "text", "text": {"content": comment}}],
                },
            },
        )
        print(f"🧾 Добавлен новый ученик: {fio} (дата оплаты: {payment_date})")


    async def add_all_students(self):
        """Добавляет всех учеников из students.json и обновляет JSON."""
        students = self.load_students()
        for student in students:
            await self.add_student_to_payments(student)
        print(f"🎉 Все {len(students)} учеников добавлены в таблицу оплат!")

    async def mark_payment(self, identifier: str, status: str = "Оплатил", month: Optional[str] = None):
        """Отмечает оплату ученика."""

        # Определяем месяц по умолчанию
        if not month:
            month = date.today().strftime("%B")
            month_map = {
                "January": "Январь", "February": "Февраль", "March": "Март",
                "April": "Апрель", "May": "Май", "June": "Июнь",
                "July": "Июль", "August": "Август", "September": "Сентябрь",
                "October": "Октябрь", "November": "Ноябрь", "December": "Декабрь",
            }
            month = month_map.get(month, month)

        print(f"🔍 Ищу ученика '{identifier}' для отметки оплаты за {month}...")

        # 1️⃣ Сначала ищем по ФИО
        response = await self.notion.databases.query(
            database_id=self.database_id,
            filter={"property": "ФИО", "rich_text": {"equals": identifier}},
        )

        # Если по ФИО нашли — это один ученик
        if response["results"]:
            results = response["results"]
        else:
            # 2️⃣ Иначе ищем по номеру телефона
            response = await self.notion.databases.query(
                database_id=self.database_id,
                filter={"property": "Phone", "phone_number": {"contains": identifier}},
            )
            results = response["results"]

        if not results:
            print(f"⚠️ Ученик '{identifier}' не найден.")
            return

        # Проверяем наличие месяца
        db_info = await self.notion.databases.retrieve(database_id=self.database_id)
        props = db_info.get("properties", {})

        if month not in props:
            print(f"📘 Месяц '{month}' отсутствует — создаю столбец...")
            await self.add_month_column(month)

        # 3️⃣ Обновляем ВСЕ найденные записи
        for item in results:
            page_id = item["id"]
            # Check if FIO exists before accessing
            fio_prop = item["properties"]["ФИО"]["rich_text"]
            fio = fio_prop[0]["plain_text"] if fio_prop else "Unknown"

            try:
                await self.notion.pages.update(
                    page_id=page_id,
                    properties={month: {"select": {"name": status}}}
                )
                print(f" ✅ {fio} → '{status}' ({month})")
            except Exception as e:
                print(f" ❌ Ошибка при обновлении {fio}: {e}")


    async def update_comment(self, identifier: str, comment: str):
        """Обновляет комментарий к оплате ученика."""
        print(f"🔍 Ищу ученика '{identifier}' для обновления комментария...")
        
        # 1️⃣ Сначала ищем по ФИО
        response = await self.notion.databases.query(
            database_id=self.database_id,
            filter={"property": "ФИО", "rich_text": {"equals": identifier}},
        )
        
        # Если по ФИО нашли — это один ученик
        if response["results"]:
            results = response["results"]
        else:
            # 2️⃣ Иначе ищем по номеру телефона
            response = await self.notion.databases.query(
                database_id=self.database_id,
                filter={"property": "Phone", "phone_number": {"contains": identifier}},
            )
            results = response["results"]
        
        if not results:
            print(f"⚠️ Ученик '{identifier}' не найден.")
            return
        
        # 3️⃣ Обновляем ВСЕ найденные записи
        for item in results:
            page_id = item["id"]
            fio_prop = item["properties"]["ФИО"]["rich_text"]
            fio = fio_prop[0]["plain_text"] if fio_prop else "Unknown"
            
            try:
                await self.notion.pages.update(
                    page_id=page_id,
                    properties={"Комментарий": {"rich_text": [{"type": "text", "text": {"content": comment}}]}}
                )
                print(f" ✅ Комментарий обновлен для {fio}")
            except Exception as e:
                print(f" ❌ Ошибка при обновлении комментария для {fio}: {e}")
        
        # Синхронизируем данные
        fetcher = NotionPaymentsFetcher(self.city_name)
        await fetcher.build_payments()

    async def close(self):
        pass

# # -----------------------------------------------------------
# # ПОЛНЫЙ ТЕСТ ВСЕХ МЕТОДОВ МОДУЛЯ
# # -----------------------------------------------------------
# if __name__ == "__main__":
#     import asyncio
#
#     async def test_all_methods():
#         city = "Magas_test"
#         updater = NotionPaymentUpdater(city)
#
#         print("\n=== TEST 1: Add month ===")
#         await updater.add_month_column("TestMonth")
#
#         print("\n=== TEST 2: Load students ===")
#         students = updater.load_students()
#         if not students:
#             print("[ERROR] No students in students.json")
#             return
#
#         test_student = students[0]
#         print(f"   Using student: {test_student['ФИО']}")
#
#         print("\n=== TEST 3: Add student to payments ===")
#         await updater.add_student_to_payments(test_student, payment_date="10 числа")
#
#         print("\n=== TEST 4: Add all students ===")
#         await updater.add_all_students()
#
#         print("\n=== TEST 5: Mark payment by FIO ===")
#         await updater.mark_payment(test_student["ФИО"], "Оплатил", month="TestMonth")
#
#         print("\n=== TEST 6: Mark payment by Phone ===")
#         phone = test_student.get("Номер родителя", "")
#         if phone:
#             await updater.mark_payment(phone, "Не оплатил", month="TestMonth")
#         else:
#             print("[WARN] No phone, skipping phone test")
#
#         print("\n[SUCCESS] All tests completed!")
#
#     asyncio.run(test_all_methods())
