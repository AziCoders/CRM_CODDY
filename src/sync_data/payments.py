import os
import json
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from notion_client import AsyncClient
from src.config import ROOT_DIR


class NotionPaymentsFetcher:
    """Загружает общую таблицу 'Оплата' и сохраняет её в payments.json"""

    def __init__(self, city_name: str):
        load_dotenv()
        self.city_name = city_name.capitalize()
        self.notion = AsyncClient(auth=os.getenv("NOTION_API_KEY"))
        self.root_dir = ROOT_DIR

        # === Пути ===
        self.students_path = self.root_dir / f"data/{self.city_name}/students.json"
        self.output_path = self.root_dir / f"data/{self.city_name}/payments.json"
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

        # === ID таблицы из .env ===
        self.database_id = os.getenv(f"{self.city_name.upper()}_PAYMENT_ID")
        if not self.database_id:
            raise ValueError(f"❌ В .env не найден ключ {self.city_name.upper()}_PAYMENT_ID")

        # === Карта учеников (ФИО → {id, url}) ===
        self.student_map = {}

    def load_students(self):
        """Создаёт карту учеников по ФИО для связывания с оплатами."""
        if not self.students_path.exists():
            print(f"⚠️ Файл {self.students_path} не найден — связь с учениками не будет установлена.")
            return

        with open(self.students_path, "r", encoding="utf-8") as f:
            students_data = json.load(f)

        for group_data in students_data.values():
            for student in group_data.get("students", []):
                name = student["ФИО"].strip().lower()
                self.student_map[name] = {
                    "id": student["ID"],
                    "url": student.get("student_url", "")
                }

        print(f"📘 Загружено {len(self.student_map)} учеников для связи с оплатами.")

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
        """Получает описание всех столбцов базы."""
        db = await self.notion.databases.retrieve(database_id=database_id)
        return db.get("properties", {})

    def parse_payment(self, item: dict, dynamic_fields: list) -> dict:
        """Преобразует запись оплаты в читаемый формат."""
        props = item.get("properties", {})

        def get_text(field):
            value = props.get(field)
            if not value:
                return ""
            if "title" in value:
                parts = value["title"]
            elif "rich_text" in value:
                parts = value["rich_text"]
            else:
                parts = []
            return "".join([p["plain_text"] for p in parts]) if parts else ""

        def get_phone(field):
            return props.get(field, {}).get("phone_number") or ""

        def get_select(field):
            v = props.get(field, {}).get("select")
            return v["name"] if v else ""

        fio = get_text("ФИО").strip()
        fio_key = fio.lower()
        student_info = self.student_map.get(fio_key, {"id": "", "url": ""})

        # === Собираем месяцы в payments_data ===
        payments_data = {
            field: get_select(field)
            for field in dynamic_fields
        }

        # === Основная запись ===
        record = {
            "ID": item["id"],
            "payment_url": f"https://www.notion.so/{item['id'].replace('-', '')}",
            "Дата оплаты": get_text("Дата оплаты"),
            "ФИО": fio,
            "student_id": student_info["id"],
            "student_url": student_info["url"],
            "Phone": get_phone("Phone"),
            "Комментарий": get_text("Комментарий"),
            "payments_data": payments_data,  # 👈 теперь все месяцы здесь
        }

        return record

    async def build_payments(self):
        """Сохраняет данные из общей таблицы оплат."""
        print(f"🔍 Загружаю общую таблицу оплат для города: {self.city_name}")

        # Загружаем карту учеников
        self.load_students()

        try:
            props = await self.get_database_properties(self.database_id)

            # Определяем динамические месяцы
            dynamic_fields = [
                name
                for name in props.keys()
                if name not in ("Дата оплаты", "ФИО", "Phone", "Комментарий")
            ]

            records = await self.fetch_all_records(self.database_id)
            parsed = [self.parse_payment(r, dynamic_fields) for r in records]
            total = len(parsed)

            all_payments = {
                "database_id": self.database_id,
                "city": self.city_name,
                "total_records": total,
                "fields": ["Дата оплаты", "ФИО", "Phone", "Комментарий"] + dynamic_fields,
                "payments": parsed,
            }

            with open(self.output_path, "w", encoding="utf-8") as f:
                json.dump(all_payments, f, ensure_ascii=False, indent=4)

            print(f"✅ Успешно сохранено: {total} записей в {self.output_path}")

        except Exception as e:
            print(f"⚠️ Ошибка при загрузке таблицы оплат: {e}")

    async def close(self):
        await self.notion.close()
