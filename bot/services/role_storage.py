"""Сервис для работы с хранилищем ролей"""
import json
import tempfile
from pathlib import Path
from typing import Dict, Optional, Any, List
from bot.config import ROLES_FILE


class RoleStorage:
    """Класс для работы с roles.json"""
    
    def __init__(self, file_path: Path = ROLES_FILE):
        self.file_path = file_path
        self.ensure_file_exists()
    
    def ensure_file_exists(self) -> None:
        """Создает файл roles.json если его нет"""
        try:
            if not self.file_path.exists():
                self.file_path.parent.mkdir(parents=True, exist_ok=True)
                with open(self.file_path, "w", encoding="utf-8") as f:
                    json.dump({}, f, ensure_ascii=False, indent=2)
        except Exception as e:
            raise RuntimeError(f"❌ Ошибка при создании файла ролей: {e}")
    
    def load_roles(self) -> Dict[str, Any]:
        """Загружает роли из файла"""
        try:
            if not self.file_path.exists():
                return {}
            
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Конвертируем ключи в строки для единообразия
                return {str(k): v for k, v in data.items()}
        except json.JSONDecodeError:
            return {}
        except Exception as e:
            print(f"⚠️ Ошибка при загрузке ролей: {e}")
            return {}
    
    def save_roles(self, data: Dict[str, Any]) -> None:
        """Сохраняет роли в файл (атомарная запись)"""
        try:
            # Записываем во временный файл
            temp_file = self.file_path.with_suffix('.tmp')
            
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            # Атомарная замена
            temp_file.replace(self.file_path)
        except Exception as e:
            raise RuntimeError(f"❌ Ошибка при сохранении ролей: {e}")
    
    def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получает данные пользователя по ID"""
        roles = self.load_roles()
        return roles.get(str(user_id))
    
    def add_user(
        self, 
        user_id: int, 
        fio: str, 
        username: str, 
        role: str, 
        city: str = "all"
    ) -> None:
        """Добавляет или обновляет пользователя"""
        roles = self.load_roles()
        roles[str(user_id)] = {
            "fio": fio,
            "username": username,
            "role": role,
            "city": city
        }
        self.save_roles(roles)
    
    def user_exists(self, user_id: int) -> bool:
        """Проверяет существование пользователя"""
        roles = self.load_roles()
        return str(user_id) in roles
    
    def is_owner(self, user_id: int) -> bool:
        """Проверяет, является ли пользователь владельцем"""
        from bot.config import OWNER_ID
        return user_id == OWNER_ID
    
    def get_all_users(self) -> List[Dict[str, Any]]:
        """Получает список всех пользователей"""
        roles = self.load_roles()
        users = []
        
        for user_id_str, user_data in roles.items():
            user_data["user_id"] = int(user_id_str)
            users.append(user_data)
        
        # Сортируем по ФИО
        users.sort(key=lambda x: x.get("fio", ""))
        
        return users
    
    def remove_user(self, user_id: int) -> bool:
        """Удаляет пользователя из системы"""
        roles = self.load_roles()
        user_id_str = str(user_id)
        
        if user_id_str not in roles:
            return False
        
        # Не позволяем удалять владельца
        from bot.config import OWNER_ID
        if user_id == OWNER_ID:
            return False
        
        del roles[user_id_str]
        self.save_roles(roles)
        return True

