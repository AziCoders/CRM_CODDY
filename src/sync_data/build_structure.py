import json
import asyncio
from src.config import ROOT_DIR, get_notion_client


class NotionStructureBuilder:
    """Формирует структуру подстраниц и баз данных для всех групп города."""

    def __init__(self, city_name: str):
        self.city_name = city_name.capitalize()
        # Use shared client
        self.notion = get_notion_client()

        # === Пути ===
        self.root_dir = ROOT_DIR
        self.groups_path = self.root_dir / f"data/{self.city_name}/groups.json"
        self.output_path = self.root_dir / f"data/{self.city_name}/structure.json"
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

    async def fetch_all_blocks(self, block_id: str) -> list:
        """Асинхронно получает все блоки страницы/базы (с поддержкой пагинации)."""
        blocks = []
        response = await self.notion.blocks.children.list(block_id=block_id)
        blocks.extend(response["results"])

        while response.get("has_more"):
            response = await self.notion.blocks.children.list(
                block_id=block_id, start_cursor=response["next_cursor"]
            )
            blocks.extend(response["results"])
        return blocks

    async def get_child_database_id(self, page_id: str) -> str:
        """Ищет внутри подстраницы единственную базу данных и возвращает её ID."""
        try:
            blocks = await self.fetch_all_blocks(page_id)
            for block in blocks:
                if block["type"] == "child_database":
                    return block["id"]
        except Exception as e:
            print(f"⚠️ Ошибка при получении подстраницы {page_id}: {e}")
        return ""

    async def process_group(self, group_id: str, group_name: str) -> dict:
        """Обрабатывает одну группу: ищет все подстраницы и ID их баз данных."""
        structure = {
            "group_name": group_name,
            "student_db_id": "",
            "attendance_db_id": "",
            "payment_db_id": "",
        }

        try:
            # Получаем подстраницы внутри группы
            blocks = await self.fetch_all_blocks(group_id)
            child_pages = [
                {"title": b["child_page"]["title"], "id": b["id"]}
                for b in blocks
                if b["type"] == "child_page"
            ]

            for page in child_pages:
                title = page["title"].lower()
                page_id = page["id"]

                db_id = await self.get_child_database_id(page_id)

                if "ученик" in title:
                    structure["student_db_id"] = db_id
                elif "посещ" in title:
                    structure["attendance_db_id"] = db_id
                elif "оплат" in title:
                    structure["payment_db_id"] = db_id

                print(f"  🔸 {page['title']} → {db_id}")

        except Exception as e:
            print(f"⚠️ Ошибка при обработке группы {group_name}: {e}")

        return structure

    async def build_structure(self):
        """Основной метод: проходит по всем группам и сохраняет structure.json."""
        if not self.groups_path.exists():
            raise FileNotFoundError(f"Файл {self.groups_path} не найден")

        with open(self.groups_path, "r", encoding="utf-8") as f:
            groups = json.load(f)

        print(f"🔍 Начинаю обработку {len(groups)} групп...")

        tasks = [
            self.process_group(group_id, info["Название группы"])
            for group_id, info in groups.items()
        ]
        results = await asyncio.gather(*tasks)

        structure = {
            group_id: result
            for (group_id, _), result in zip(groups.items(), results)
        }

        with open(self.output_path, "w", encoding="utf-8") as f:
            json.dump(structure, f, ensure_ascii=False, indent=4)

        print(f"\n✅ Структура сохранена: {self.output_path}")

    async def close(self):
        """
        Does nothing now as we use a shared client.
        Kept for backward compatibility.
        """
        pass
