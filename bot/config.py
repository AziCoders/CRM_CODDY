"""Конфигурация бота"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Корневая директория проекта
ROOT_DIR = Path(__file__).resolve().parent.parent

# Путь к файлу ролей
# Важно для деплоя: можно вынести роли в постоянное хранилище вне папки релиза
# Пример: ROLES_FILE=/var/lib/mybot/roles.json
ROLES_FILE = Path(os.getenv("ROLES_FILE", str(ROOT_DIR / "roles.json"))).expanduser()

# ID владельца из .env
OWNER_ID = int(os.getenv("OWNER_ID", "0"))

# Токен бота
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# Список городов для выбора
# CITIES = ["Назрань", "Магас", "Сунжа", "Карабулак", "Малгобек"]
CITIES = ["Назрань", "Магас", "Сунжа", "Карабулак", "Малгобек", "ШК22Н", "ШК4Н"]

# Маппинг городов для Notion (русские названия -> английские)
CITY_MAPPING = {
    "Назрань": "Nazran",
    "Магас": "Magas",
    "Сунжа": "Sunja",
    "Карабулак": "Karabulak",
    "Малгобек": "Malgobek",
    "ШК22Н": "Magas_test",  # Предположение, нужно уточнить
    "ШК4Н": "Magas_test",   # Предположение, нужно уточнить
}

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN не найден в переменных окружения")

if OWNER_ID == 0:
    raise ValueError("❌ OWNER_ID не найден в переменных окружения")

