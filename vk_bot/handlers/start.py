"""Обработчик команды start для VK бота"""
from vkbottle.bot import BotLabeler, Message
from vkbottle import BaseStateGroup
from vk_bot.services.role_storage import RoleStorage
from vk_bot.config import VK_OWNER_ID

labeler = BotLabeler()
storage = RoleStorage()

@labeler.private_message(text="start")
@labeler.private_message(payload={"command": "start"})
async def start_handler(message: Message):
    """Обработчик команды start"""
    user_id = message.from_id
    user_info = await message.get_user()
    
    # Проверяем роль
    user_data = storage.get_user(user_id)
    
    if not user_data:
        # Регистрация
        await message.answer(
            "👋 Добро пожаловать!\n\n"
            "Для начала работы необходимо пройти регистрацию.\n"
            "Введите ваше ФИО полностью:"
        )
        # Здесь нужно будет установить стейт, но пока просто заглушка
        # В vkbottle стейты работают немного иначе, чем в aiogram
        return

    role = user_data.get("role")
    if role == "pending":
        await message.answer("⏳ Ваша заявка на рассмотрении.")
        return
        
    await message.answer(f"С возвращением! Ваша роль: {role}")
