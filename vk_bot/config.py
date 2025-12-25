"""Конфигурация VK бота"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Корневая директория проекта
ROOT_DIR = Path(__file__).resolve().parent.parent

# Путь к файлу ролей (отдельный файл для VK, чтобы не пересекались ID)
# Важно для деплоя: можно вынести роли в постоянное хранилище вне папки релиза
# Пример: VK_ROLES_FILE=/var/lib/mybot/roles_vk.json
ROLES_FILE = Path(os.getenv("VK_ROLES_FILE", str(ROOT_DIR / "roles_vk.json"))).expanduser()

# Токен бота
VK_BOT_TOKEN = os.getenv("VK_BOT_TOKEN", "")

# ID владельца (VK ID)
# Можно добавить VK_OWNER_ID в .env или хардкодить, если известен
VK_OWNER_ID = int(os.getenv("VK_OWNER_ID", "0"))

if not VK_BOT_TOKEN:
    print("⚠️ VK_BOT_TOKEN не найден в переменных окружения")
