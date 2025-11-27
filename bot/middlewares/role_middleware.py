"""Middleware для проверки ролей пользователей"""
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update, Message, CallbackQuery, InlineQuery
from bot.services.role_storage import RoleStorage
from bot.config import OWNER_ID


class RoleMiddleware(BaseMiddleware):
    """Middleware для проверки и инъекции роли пользователя"""
    
    def __init__(self):
        self.storage = RoleStorage()
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """Обрабатывает обновление и добавляет роль пользователя"""
        # Получаем user из события
        user = None
        
        # Проверяем тип события
        if isinstance(event, Message):
            user = event.from_user
        elif isinstance(event, CallbackQuery):
            user = event.from_user
        elif isinstance(event, InlineQuery):
            user = event.from_user
        elif isinstance(event, Update):
            # Если это Update, извлекаем из него событие
            if event.message:
                user = event.message.from_user
            elif event.callback_query:
                user = event.callback_query.from_user
            elif event.inline_query:
                user = event.inline_query.from_user
        
        if not user:
            return await handler(event, data)
        
        user_id = user.id
        
        # Проверяем, является ли пользователь владельцем
        if user_id == OWNER_ID:
            data["user_role"] = "owner"
            data["user_city"] = "all"
        else:
            # Загружаем роль из хранилища
            user_data = self.storage.get_user(user_id)
            if user_data:
                data["user_role"] = user_data.get("role")
                data["user_city"] = user_data.get("city", "all")
            else:
                data["user_role"] = None
                data["user_city"] = None
        
        # Сохраняем данные пользователя
        data["user_id"] = user_id
        data["user_fio"] = user.full_name
        data["username"] = user.username or ""
        
        return await handler(event, data)

