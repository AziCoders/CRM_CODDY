import os
import json
from src.config import ROOT_DIR, get_notion_client


class NotionPageFetcher:
    """Класс для получения данных о странице города из Notion."""

    def __init__(self, city_name: str):
        self.city_name = city_name.capitalize()
        # Use shared client
        self.notion = get_notion_client()
        self.page_id = os.getenv(f"{self.city_name.upper()}_PAGE_ID")

        if not self.page_id:
            raise ValueError(f"❌ Переменная {self.city_name.upper()}_PAGE_ID не найдена в .env")

        # === 🔧 Главное изменение ===
        # Теперь корень проекта — это папка "Final Product"
        self.root_dir = ROOT_DIR

        # путь сохранения — data/{city}/main_page_info.json
        self.output_path = self.root_dir / f"data/{self.city_name}/main_page_info.json"
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

    async def get_page_content(self) -> list:
        """Асинхронно получает все блоки страницы."""
        blocks = []
        response = await self.notion.blocks.children.list(block_id=self.page_id)
        blocks.extend(response["results"])

        # Если страница большая — догружаем следующие страницы
        while response.get("has_more"):
            response = await self.notion.blocks.children.list(
                block_id=self.page_id, start_cursor=response["next_cursor"]
            )
            blocks.extend(response["results"])

        return blocks

    @staticmethod
    def extract_info_section(blocks: list) -> dict:
        """Извлекает текст из раздела 'Информация' и формирует словарь."""
        info_section = False
        data = {
            "address": "",
            "office_hours": "",
            "teacher": "",
            "contact": "",
            "number_seats": "",
        }

        for block in blocks:
            block_type = block["type"]
            texts = block.get(block_type, {}).get("rich_text", [])
            text = "".join(t.get("plain_text", "") for t in texts).strip()

            if text == "Информация":
                info_section = True
                continue
            if info_section and text in ("Таблицы", "Шаблоны"):
                break

            if info_section and text:
                if "Адрес" in text:
                    data["address"] = text
                elif "Время работы" in text:
                    data["office_hours"] = text
                elif "Преподаватель" in text:
                    data["teacher"] = text
                elif "Контакты" in text:
                    data["contact"] = text
                elif "Кол-во мест" in text:
                    data["number_seats"] = text

        return data

    async def save_info_to_file(self):
        """Главный метод — получает страницу и сохраняет только раздел 'Информация'."""
        print(f"🔄 Загрузка страницы для города: {self.city_name}...")
        blocks = await self.get_page_content()
        info_data = self.extract_info_section(blocks)

        with open(self.output_path, "w", encoding="utf-8") as f:
            json.dump(info_data, f, ensure_ascii=False, indent=4)

        print(f"✅ Информация сохранена в {self.output_path}")
