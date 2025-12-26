"""
Забирает данные всех групп и сохраняет их в файле groups.json по пути data/{city_name}/groups.json.

Формат сохранения:
    "id": "28bd06fc-f646-80e6-87a1-c07aa3e3ca05": {
        "Название группы": "Шаблон группа 2.0",
        "Город": "",
        "Дата создания": "",
        "Статус группы": "",
        "Тариф": "",
        "Расписание": "",
        "Количество учеников": "",
        "Преподаватель": "",
        "Комментарии": ""}
"""

import os
import json
from pathlib import Path
from notion_client import AsyncClient
from dotenv import load_dotenv
from src.config import ROOT_DIR, get_notion_client


class NotionGroupFetcher:
    """Класс для получения таблицы групп из Notion."""

    def __init__(self, city_name: str):
        load_dotenv()
        self.city_name = city_name.capitalize()
        # Use shared client
        self.notion = get_notion_client()
        self.database_id = os.getenv(f"{self.city_name.upper()}_GROUP_ID")

        if not self.database_id:
            raise ValueError(f"❌ Переменная {self.city_name.upper()}_GROUP_ID не найдена в .env")

        # === Определяем корень проекта ===
        self.root_dir = ROOT_DIR

        # === Путь сохранения ===
        self.output_path = self.root_dir / f"data/{self.city_name}/groups.json"
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

    async def get_all_groups(self) -> list:
        """Асинхронно получает все записи из таблицы групп."""
        all_results = []
        has_more = True
        next_cursor = None

        print(f"🔄 Загрузка таблицы групп для города: {self.city_name}...")

        while has_more:
            response = await self.notion.databases.query(
                database_id=self.database_id,
                start_cursor=next_cursor
            )
            all_results.extend(response["results"])
            has_more = response.get("has_more", False)
            next_cursor = response.get("next_cursor")

        print(f"✅ Загружено {len(all_results)} записей из таблицы.")
        return all_results

    # === безопасное извлечение данных из Notion ===
    @staticmethod
    def safe_get(prop: dict, *keys, default=""):
        """Безопасно достаёт вложенные значения."""
        value = prop
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return default
        return value if value is not None else default

    @staticmethod
    def extract_group_fields(records: list) -> list:
        """Извлекает ключевые поля группы из Notion-записей."""
        groups = {}

        for item in records:
            props = item.get("properties", {})

            title_list = NotionGroupFetcher.safe_get(props, "Название группы", "title", default=[])
            title_text = title_list[0].get("plain_text") if title_list and isinstance(title_list, list) else ""

            groups[item.get("id", "")] = {
                "Название группы": title_text,
                "Город": NotionGroupFetcher.safe_get(props, "Город", "select", "name"),
                "Дата создания": NotionGroupFetcher.safe_get(props, "Дата создания", "date", "start"),
                "Статус группы": NotionGroupFetcher.safe_get(props, "Статус группы", "select", "name"),
                "Тариф": NotionGroupFetcher.safe_get(props, "Тариф", "select", "name"),
                "Расписание": NotionGroupFetcher.safe_get(props, "Расписание", "rich_text", default=[]),
                "Количество учеников": NotionGroupFetcher.safe_get(props, "Количество учеников", "number"),
                "Преподаватель": NotionGroupFetcher.safe_get(props, "Преподаватель", "select", "name"),
                "Комментарии": NotionGroupFetcher.safe_get(props, "Комментарии", "rich_text", default=[]),
            }

        # Преобразуем rich_text в читаемый текст
        for g in groups.values():
            if isinstance(g["Расписание"], list):
                g["Расписание"] = "".join(rt.get("plain_text", "") for rt in g["Расписание"])
            if isinstance(g["Комментарии"], list):
                g["Комментарии"] = "".join(rt.get("plain_text", "") for rt in g["Комментарии"])

        return groups

    async def save_groups_to_file(self):
        """Главный метод — получает данные и сохраняет их в JSON."""
        records = await self.get_all_groups()
        parsed_data = self.extract_group_fields(records)

        with open(self.output_path, "w", encoding="utf-8") as f:
            json.dump(parsed_data, f, ensure_ascii=False, indent=4)

        print(f"📁 Данные успешно сохранены в {self.output_path}")

