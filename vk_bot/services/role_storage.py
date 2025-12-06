"""Сервис для работы с хранилищем ролей (обертка для VK)"""
from bot.services.role_storage import RoleStorage as OriginalRoleStorage
from vk_bot.config import ROLES_FILE

class RoleStorage(OriginalRoleStorage):
    """Класс для работы с roles_vk.json"""
    
    def __init__(self):
        super().__init__(file_path=ROLES_FILE)
