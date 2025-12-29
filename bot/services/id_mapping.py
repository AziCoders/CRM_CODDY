"""Сервис для маппинга коротких ID на полные UUID"""
import time
from typing import Dict, Optional
from collections import defaultdict


class IdMappingService:
    """Сервис для управления маппингом коротких ID (2 цифры) на полные UUID"""
    
    def __init__(self):
        # Хранилище маппингов: {тип: {короткий_id: {"full_id": "...", "created_at": ...}}}
        self._mappings: Dict[str, Dict[str, Dict]] = defaultdict(dict)
        # Счетчики для генерации уникальных коротких ID
        self._counters: Dict[str, int] = defaultdict(int)
        # Время жизни маппинга в секундах (1 час)
        self._ttl = 3600
    
    def generate_short_id(self, mapping_type: str) -> str:
        """Генерирует уникальный короткий ID (2 цифры) для типа маппинга"""
        counter = self._counters[mapping_type]
        short_id = f"{counter:02d}"  # Формат: 00, 01, 02, ..., 99
        self._counters[mapping_type] = (counter + 1) % 100  # Циклический счетчик 0-99
        return short_id
    
    def add_mapping(self, mapping_type: str, full_id: str) -> str:
        """
        Добавляет маппинг полного ID на короткий
        
        Args:
            mapping_type: Тип маппинга ('group' или 'student')
            full_id: Полный UUID
            
        Returns:
            Короткий ID (2 цифры)
        """
        # Очищаем старые записи перед добавлением
        self._cleanup_old_mappings(mapping_type)
        
        # Генерируем новый короткий ID
        short_id = self.generate_short_id(mapping_type)
        
        # Сохраняем маппинг
        self._mappings[mapping_type][short_id] = {
            "full_id": full_id,
            "created_at": time.time()
        }
        
        return short_id
    
    def get_full_id(self, mapping_type: str, short_id: str) -> Optional[str]:
        """
        Получает полный ID по короткому
        
        Args:
            mapping_type: Тип маппинга ('group' или 'student')
            short_id: Короткий ID (2 цифры)
            
        Returns:
            Полный UUID или None если не найден
        """
        mapping = self._mappings[mapping_type].get(short_id)
        if not mapping:
            return None
        
        # Проверяем, не истек ли срок действия
        if time.time() - mapping["created_at"] > self._ttl:
            del self._mappings[mapping_type][short_id]
            return None
        
        return mapping["full_id"]
    
    def _cleanup_old_mappings(self, mapping_type: str) -> None:
        """Очищает устаревшие маппинги для указанного типа"""
        current_time = time.time()
        expired_keys = [
            key for key, value in self._mappings[mapping_type].items()
            if current_time - value["created_at"] > self._ttl
        ]
        for key in expired_keys:
            del self._mappings[mapping_type][key]
    
    def clear_mappings(self, mapping_type: Optional[str] = None) -> None:
        """
        Очищает все маппинги
        
        Args:
            mapping_type: Если указан, очищает только этот тип, иначе все
        """
        if mapping_type:
            self._mappings[mapping_type].clear()
            self._counters[mapping_type] = 0
        else:
            self._mappings.clear()
            self._counters.clear()


# Глобальный экземпляр сервиса
id_mapping_service = IdMappingService()

