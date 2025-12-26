import os
import json
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from notion_client import AsyncClient
from src.config import ROOT_DIR


class NotionAttendanceFetcher:
    """Загружает таблицы 'Посещаемость' из всех групп и сохраняет их в attendance.json"""

    def __init__(self, city_name: str):
        load_dotenv()
        self.city_name = city_name.capitalize()
        self.notion = AsyncClient(auth=os.getenv("NOTION_API_KEY"))

        # === Определяем корень проекта "Final Product" ===
        self.root_dir = ROOT_DIR

        # === Пути ===
        self.structure_path = self.root_dir / f"data/{self.city_name}/structure.json"
        self.students_path = self.root_dir / f"data/{self.city_name}/students.json"
        self.output_path = self.root_dir / f"data/{self.city_name}/attendance.json"
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

        # === Словарь для подстановки данных учеников ===
        self.student_map = {}

    async def fetch_all_records(self, database_id: str) -> list:
        """Получает все записи из базы Notion (с пагинацией)."""
        results = []
        response = await self.notion.databases.query(database_id=database_id)
        results.extend(response["results"])

        while response.get("has_more"):
            response = await self.notion.databases.query(
                database_id=database_id,
                start_cursor=response["next_cursor"],
            )
            results.extend(response["results"])

        return results

    async def get_database_properties(self, database_id: str) -> dict:
        """Получает описание всех столбцов в базе."""
        db = await self.notion.databases.retrieve(database_id=database_id)
        return db.get("properties", {})

    def load_students(self):
        """Создаёт карту ID -> {'name': ФИО, 'url': ссылка} из students.json."""
        if not self.students_path.exists():
            print(f"⚠️ Файл {self.students_path} не найден, ФИО и ссылки не будут подставлены.")
            return

        with open(self.students_path, "r", encoding="utf-8") as f:
            students_data = json.load(f)

        for group_data in students_data.values():
            for student in group_data.get("students", []):
                self.student_map[student["ID"]] = {
                    "name": student["ФИО"],
                    "url": student.get("student_url", ""),
                }

        print(f"📘 Загружено {len(self.student_map)} учеников для подстановки ФИО и ссылок.")

    def parse_attendance(self, item: dict, dynamic_fields: list) -> dict:
        """Преобразует запись посещаемости в читаемый формат."""
        props = item.get("properties", {})

        def get_text(field):
            text_field = props.get(field, {}).get("title")
            if text_field and len(text_field) > 0:
                return text_field[0]["plain_text"]
            return ""

        def get_relation(field):
            rel = props.get(field, {}).get("relation")
            if not rel:
                return "", "", ""
            rel_id = rel[0]["id"]
            student_data = self.student_map.get(rel_id, {})
            name = student_data.get("name", rel_id)
            url = student_data.get("url", "")
            return rel_id, name, url

        def get_select(field):
            v = props.get(field, {}).get("select")
            return v["name"] if v else ""

        # Основная часть записи
        record = {
            "ID": item["id"],
            "№": get_text("№"),
        }

        # Извлекаем данные ученика
        student_id, name, url = get_relation("ФИО")
        record["student_id"] = student_id
        record["ФИО"] = name
        record["student_url"] = url

        # Формируем блок "attendance"
        attendance_data = {}
        for field in dynamic_fields:
            value = get_select(field)
            attendance_data[field] = value

        record["attendance"] = attendance_data
        return record

    async def build_attendance(self):
        """Проходит по всем группам и сохраняет посещаемость из каждой таблицы."""
        if not self.structure_path.exists():
            raise FileNotFoundError(f"Файл {self.structure_path} не найден")

        # === Загружаем карту учеников ===
        self.load_students()

        with open(self.structure_path, "r", encoding="utf-8") as f:
            structure = json.load(f)

        all_attendance = {}
        total_records = 0

        print(f"🔍 Начинаю загрузку посещаемости из {len(structure)} групп...\n")

        for group_id, info in structure.items():
            db_id = info.get("attendance_db_id")
            if not db_id:
                print(f"⚠️ У группы '{info['group_name']}' нет attendance_db_id, пропуск.")
                continue

            try:
                props = await self.get_database_properties(db_id)
                dynamic_fields = [
                    name
                    for name in props.keys()
                    if name not in ("№", "ФИО")
                ]

                records = await self.fetch_all_records(db_id)
                parsed = [self.parse_attendance(r, dynamic_fields) for r in records]
                total = len(parsed)
                total_records += total

                all_attendance[group_id] = {
                    "group_name": info["group_name"],
                    "total_records": total,
                    "fields": ["№", "ФИО"] + dynamic_fields,
                    "attendance": parsed,
                }

                print(f"✅ {info['group_name']} — {total} записей, столбцов: {len(dynamic_fields) + 2}")
            except Exception as e:
                print(f"⚠️ Ошибка при обработке {info['group_name']}: {e}")

        with open(self.output_path, "w", encoding="utf-8") as f:
            json.dump(all_attendance, f, ensure_ascii=False, indent=4)

        print(f"\n📁 Посещаемость сохранена: {self.output_path}")
        print(f"📊 Всего записей по городу {self.city_name}: {total_records}")

    async def close(self):
        await self.notion.close()
