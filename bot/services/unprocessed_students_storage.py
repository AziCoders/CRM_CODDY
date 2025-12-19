"""Сервис для хранения необработанных учеников"""
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from bot.config import ROOT_DIR


class UnprocessedStudentsStorage:
    """Класс для работы с необработанными учениками"""
    
    def __init__(self, file_path: Path = None):
        if file_path is None:
            file_path = ROOT_DIR / "data" / "unprocessed_students.json"
        self.file_path = file_path
        self.ensure_file_exists()
    
    def ensure_file_exists(self) -> None:
        """Создает файл если его нет"""
        try:
            if not self.file_path.exists():
                self.file_path.parent.mkdir(parents=True, exist_ok=True)
                with open(self.file_path, "w", encoding="utf-8") as f:
                    json.dump({}, f, ensure_ascii=False, indent=2)
        except Exception as e:
            raise RuntimeError(f"❌ Ошибка при создании файла необработанных учеников: {e}")
    
    def load_unprocessed(self) -> Dict[str, Any]:
        """Загружает необработанных учеников из файла"""
        try:
            if not self.file_path.exists():
                return {}
            
            with open(self.file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
        except Exception as e:
            print(f"⚠️ Ошибка при загрузке необработанных учеников: {e}")
            return {}
    
    def save_unprocessed(self, data: Dict[str, Any]) -> None:
        """Сохраняет необработанных учеников в файл (атомарная запись)"""
        try:
            temp_file = self.file_path.with_suffix('.tmp')
            
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            temp_file.replace(self.file_path)
        except Exception as e:
            raise RuntimeError(f"❌ Ошибка при сохранении необработанных учеников: {e}")
    
    def add_unprocessed_student(self, notification_id: str, student_data: Dict[str, Any]) -> None:
        """Добавляет необработанного ученика"""
        unprocessed = self.load_unprocessed()
        unprocessed[notification_id] = {
            **student_data,
            "added_at": datetime.now().isoformat()
        }
        self.save_unprocessed(unprocessed)
    
    def remove_unprocessed_student(self, notification_id: str) -> bool:
        """Удаляет необработанного ученика"""
        unprocessed = self.load_unprocessed()
        if notification_id not in unprocessed:
            return False
        
        del unprocessed[notification_id]
        self.save_unprocessed(unprocessed)
        return True
    
    def get_all_unprocessed(self) -> List[Dict[str, Any]]:
        """Получает список всех необработанных учеников"""
        unprocessed = self.load_unprocessed()
        return [
            {
                "notification_id": notif_id,
                **data
            }
            for notif_id, data in unprocessed.items()
        ]
    
    def get_unprocessed_by_notification_id(self, notification_id: str) -> Optional[Dict[str, Any]]:
        """Получает необработанного ученика по notification_id"""
        unprocessed = self.load_unprocessed()
        if notification_id not in unprocessed:
            return None
        
        return {
            "notification_id": notification_id,
            **unprocessed[notification_id]
        }
