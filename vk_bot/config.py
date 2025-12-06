"""Конфигурация VK бота"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Корневая директория проекта
ROOT_DIR = Path(__file__).resolve().parent.parent

# Путь к файлу ролей (отдельный файл для VK, чтобы не пересекались ID)
ROLES_FILE = ROOT_DIR / "roles_vk.json"

# Токен бота
VK_BOT_TOKEN = "vk1.a.kh4RS75OAgca4ST2zsJYRVJq62WDBRySKqKJEBUFMFawg4JXHgxwNNn6TecriB-lb-lhwuLDi7EQNWNSfJO5QNhLLqH-iS6lYFx6I_KOWQt1iTmmAaCsl5MaVIVqq5VaHuadUdos6dWP7Wxqqzi4w9zDTJzi-M5BcJegzWohKeno9ODevcMiLPKNY4egTp5GILAYnBPGgb9Dpt5VO4J66w"

# ID владельца (VK ID)
# Можно добавить VK_OWNER_ID в .env или хардкодить, если известен
VK_OWNER_ID = int(os.getenv("VK_OWNER_ID", "0"))

if not VK_BOT_TOKEN:
    print("⚠️ VK_BOT_TOKEN не найден в переменных окружения")
