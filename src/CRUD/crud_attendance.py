# crud_attendance.py

import os
from dotenv import load_dotenv
from notion_client import AsyncClient

import asyncio


class NotionAttendanceUpdater:
    """
    Минимальный класс:
    - add_day_column: создаёт столбец даты (select)
    - add_student_row: добавляет нового ученика в таблицу
    - mark_attendance: ставит/обновляет посещаемость (работает только по ID ученика)
    """

    SELECT_OPTIONS = [
        {"name": "Присутствовал", "color": "green"},
        {"name": "Отсутствовал", "color": "red"},
        {"name": "Отсутствовал по причине", "color": "purple"},
        {"name": "Опоздал", "color": "yellow"},
    ]

    def __init__(self):
        load_dotenv()
        self.notion = AsyncClient(auth=os.getenv("NOTION_API_KEY"))

    # -------------------------------------------------------
    # 1) Добавление столбца даты
    # -------------------------------------------------------
    async def add_day_column(self, db_id: str, date_str: str):
        """
        Создаёт столбец формата дд.мм.гггг если его нет.
        """

        db_info = await self.notion.databases.retrieve(database_id=db_id)
        props = db_info.get("properties", {})

        if date_str in props:
            print(f"⚠️ Столбец '{date_str}' уже существует — пропуск.")
            return

        await self.notion.databases.update(
            database_id=db_id,
            properties={
                date_str: {
                    "type": "select",
                    "select": {"options": self.SELECT_OPTIONS},
                }
            },
        )

        print(f"✅ Добавлен новый столбец даты: {date_str}")

    # -------------------------------------------------------
    # 2) Добавление нового ученика
    # -------------------------------------------------------
    async def add_student_row(self, db_id: str, student_id: str, number: str = "1"):
        """
        Добавляет строку ученика в таблицу посещаемости.
        НЕ создаёт дубликат, если ученик уже есть.
        """

        # проверяем, есть ли уже такая строка
        try:
            response = await self.notion.databases.query(
                database_id=db_id,
                filter={
                    "property": "ФИО",
                    "relation": {"contains": student_id},
                },
            )
        except Exception as e:
            print(f"❌ Ошибка запроса Notion: {e}")
            return

        if response["results"]:
            print(f"⚠️ Ученик {student_id} уже есть в таблице — пропуск.")
            return

        # создаём
        await self.notion.pages.create(
            parent={"database_id": db_id},
            properties={
                "№": {
                    "title": [
                        {"type": "text", "text": {"content": number}}
                    ]
                },
                "ФИО": {
                    "relation": [{"id": student_id}]
                }
            },
        )

        print(f"🧾 Добавлен новый ученик: {student_id} (№: {number})")

    # -------------------------------------------------------
    # 3) Отметка посещаемости
    # -------------------------------------------------------
    async def mark_attendance(self, db_id: str, student_id: str, date_str: str, status: str):
        """
        :param db_id: ID базы 'Посещаемость'
        :param student_id: UUID ученика (relation)
        :param date_str: 'дд.мм.гггг'
        :param status: select статус посещаемости
        """

        # 1) Проверяем/создаём столбец даты
        await self.add_day_column(db_id, date_str)

        # 2) Ищем строку по relation 'ФИО'
        try:
            response = await self.notion.databases.query(
                database_id=db_id,
                filter={
                    "property": "ФИО",
                    "relation": {"contains": student_id},
                },
            )
        except Exception as e:
            print(f"❌ Ошибка при запросе Notion: {e}")
            return

        # ------------------------------------------------
        # Если строки НЕТ → создаём новую
        # ------------------------------------------------
        if not response["results"]:
            print(f"ℹ️ У ученика {student_id} нет строки посещаемости — создаю.")

            await self.notion.pages.create(
                parent={"database_id": db_id},
                properties={
                    "№": {
                        "title": [
                            {"type": "text", "text": {"content": "1"}}
                        ]
                    },
                    "ФИО": {
                        "relation": [{"id": student_id}]
                    },
                    date_str: {
                        "select": {"name": status}
                    }
                },
            )

            print(f"✅ Строка создана: {student_id} → {status} ({date_str})")
            return

        # ------------------------------------------------
        # Если строка есть → обновляем существующую
        # ------------------------------------------------
        page_id = response["results"][0]["id"]

        await self.notion.pages.update(
            page_id=page_id,
            properties={
                date_str: {"select": {"name": status}}
            }
        )

        print(f"✅ Обновлено посещение: {student_id} → {status} ({date_str})")

    async def close(self):
        await self.notion.aclose()


# # -------------------------------------------------------
# # 🔥 ПОЛНЫЙ ТЕСТ РАБОТЫ КЛАССА NotionAttendanceUpdater
# # -------------------------------------------------------
# if __name__ == "__main__":
#     import asyncio
#
#
#     async def test_attendance():
#         updater = NotionAttendanceUpdater()
#
#         # 👉 УКАЖИ ТУТ ID базы Посещаемости своей тестовой группы
#         TEST_DB_ID = "26cd06fcf646810e9b8de17d36440a75"
#
#         # 👉 И УКАЖИ ID тестового ученика (relation)
#         TEST_STUDENT_ID = "26cd06fc-f646-8111-bad6-e565df88d200"
#
#         TEST_DATE = "23.11.2025"  # пример даты
#         TEST_STATUS = "Присутствовал"
#
#         print("\n=== ТЕСТ 1: Добавление столбца даты ===")
#         await updater.add_day_column(TEST_DB_ID, TEST_DATE)
#
#         print("\n=== ТЕСТ 2: Добавление ученика в таблицу ===")
#         await updater.add_student_row(TEST_DB_ID, TEST_STUDENT_ID, number="1")
#
#         print("\n=== ТЕСТ 3: Отметка посещаемости ===")
#         await updater.mark_attendance(TEST_DB_ID, TEST_STUDENT_ID, TEST_DATE, TEST_STATUS)
#
#         print("\n=== ТЕСТ 4: Второй вызов mark_attendance (должно обновиться, не создаст дубль) ===")
#         await updater.mark_attendance(TEST_DB_ID, TEST_STUDENT_ID, TEST_DATE, "Опоздал")
#
#         await updater.close()
#         print("\n🎉 ВСЕ ТЕСТЫ УСПЕШНО ПРОЙДЕНЫ!")
#
#
#     asyncio.run(test_attendance())
