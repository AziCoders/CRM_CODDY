import json
import asyncio
from src.config import ROOT_DIR, get_notion_client
from src.utils import normalize_phone


class NotionStudentsFetcher:
    """Загружает таблицы 'Ученики' из всех групп и сохраняет их в students.json"""

    def __init__(self, city_name: str):
        self.city_name = city_name.capitalize()
        # Use shared client
        self.notion = get_notion_client()

        # === Пути ===
        self.root_dir = ROOT_DIR
        self.structure_path = self.root_dir / f"data/{self.city_name}/structure.json"
        self.output_path = self.root_dir / f"data/{self.city_name}/students.json"
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

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

    def parse_student(self, item: dict) -> dict:
        """Преобразует запись ученика в читаемый формат (включая пустые поля)."""
        props = item.get("properties", {})

        def get_text(field):
            field_data = props.get(field, {})
            title = field_data.get("title")
            rich_text = field_data.get("rich_text")
            if title and len(title) > 0:
                return title[0].get("plain_text", "")
            if rich_text and len(rich_text) > 0:
                return rich_text[0].get("plain_text", "")
            return ""

        def get_select(field):
            v = props.get(field, {}).get("select")
            return v["name"] if v else ""

        def get_number(field):
            value = props.get(field, {}).get("number")
            return value if value is not None else ""

        def get_date(field):
            date_field = props.get(field, {}).get("date")
            return date_field.get("start") if date_field else ""

        def get_phone(field):
            phone_raw = props.get(field, {}).get("phone_number")
            if not phone_raw:
                return ""
            return normalize_phone(phone_raw)

        def get_relation(field):
            rel = props.get(field, {}).get("relation")
            return [r.get("id") for r in rel] if rel else []

        notion_url = f"https://www.notion.so/{item['id'].replace('-', '')}"

        return {
            "ID": item.get("id", ""),
            "student_url": notion_url,
            "ФИО": get_text("ФИО"),
            "Возраст": get_number("Возраст"),
            "Дата поступления": get_date("Дата поступления"),
            "Номер родителя": get_phone("Номер родителя"),
            "Имя родителя": get_text("Имя родителя"),
            "Тариф": get_select("Тариф"),
            "Статус": get_select("Статус"),
            "Город": get_select("Город"),
            "Ссылка на WA, TG": get_text("Ссылка на WA, TG"),
            "Комментарии": get_text("Комментарии"),
            "Посещаемость": get_relation("Посещаемость"),
        }

    async def build_students(self):
        """Проходит по всем группам и сохраняет учеников из каждой таблицы."""
        if not self.structure_path.exists():
            raise FileNotFoundError(f"Файл {self.structure_path} не найден")

        with open(self.structure_path, "r", encoding="utf-8") as f:
            structure = json.load(f)

        all_students = {}
        total_city_students = 0

        print(f"🔍 Начинаю загрузку учеников из {len(structure)} групп...\n")

        for group_id, info in structure.items():
            db_id = info.get("student_db_id")
            if not db_id:
                print(f"⚠️ У группы '{info['group_name']}' нет student_db_id, пропуск.")
                continue

            try:
                records = await self.fetch_all_records(db_id)
                print(f"\n=== {info['group_name']} ===")
                print(f"Всего в API пришло: {len(records)} записей")
                for r in records:
                    fio = r["properties"]["ФИО"]["title"][0]["plain_text"] if r["properties"]["ФИО"][
                        "title"] else "❌ пусто"
                    print("—", fio)

                students = [self.parse_student(r) for r in records]
                total = len(students)
                total_city_students += total

                all_students[group_id] = {
                    "group_name": info["group_name"],
                    "total_students": total,
                    "students": students,
                }

                print(f"✅ {info['group_name']} — {total} учеников.")
            except Exception as e:
                print(f"⚠️ Ошибка при обработке {info['group_name']}: {e}")

        with open(self.output_path, "w", encoding="utf-8") as f:
            json.dump(all_students, f, ensure_ascii=False, indent=4)

        print(f"\n📁 Все ученики сохранены: {self.output_path}")
        print(f"📊 Всего учеников по городу {self.city_name}: {total_city_students}")

    async def close(self):
        """
        Does nothing now as we use a shared client.
        Kept for backward compatibility.
        """
        pass


async def full_city_sync(city_name: str):
    print(f"\n🌆 === Синхронизация данных для города: {city_name.capitalize()} ===\n")

    students_fetcher = NotionStudentsFetcher(city_name)
    await students_fetcher.build_students()


if __name__ == "__main__":
    import time
    start_time = time.time()
    city = "karabulak"  # 🔧 Замени на нужный город
    asyncio.run(full_city_sync(city))
    end_time = time.time()
    print(end_time-start_time)
