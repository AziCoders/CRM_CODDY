# crud_attendance.py

import os
from dotenv import load_dotenv
from notion_client import AsyncClient

import asyncio


class NotionAttendanceUpdater:
    """
    Минимальный класс:
    - add_day_column: создаёт столбец даты (select)
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
    # 2) Отметка посещаемости (UNIQUE: принимает только student_id)
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


async def main():
    updater = NotionAttendanceUpdater()

    attendance_db_id = "269d06fc-f646-80b6-9abb-e7623a902e77"
    student_id = "26ad06fc-f646-8078-9cbe-f1878ee79c19"  # ID ученика

    await updater.mark_attendance(
        db_id=attendance_db_id,
        student_id=student_id,
        date_str="24.11.2025",
        status="Отсутствовал"
    )

    await updater.close()


asyncio.run(main())
