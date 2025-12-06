"""Обработчик назначения ролей владельцем"""
from vkbottle.bot import BotLabeler, Message
from vkbottle import BaseStateGroup
from vk_bot.services.role_storage import RoleStorage
from vk_bot.config import VK_OWNER_ID

labeler = BotLabeler()
storage = RoleStorage()

@labeler.private_message(text="approve <user_id:int> <role>")
async def approve_role(message: Message, user_id: int, role: str):
    """Назначение роли пользователю"""
    if message.from_id != VK_OWNER_ID:
        return

    if not storage.user_exists(user_id):
        await message.answer("❌ Пользователь не найден.")
        return

    user_data = storage.get_user(user_id)
    storage.add_user(
        user_id=user_id,
        fio=user_data["fio"],
        username=user_data.get("username", ""),
        role=role,
        city=user_data.get("city", "")
    )

    await message.answer(f"✅ Роль '{role}' назначена пользователю {user_data['fio']}.")
    
    # Отправляем уведомление пользователю
    try:
        await message.ctx_api.messages.send(
            peer_id=user_id,
            message=f"🎉 Вам назначена роль: {role}",
            random_id=0
        )
    except Exception as e:
        await message.answer(f"⚠️ Не удалось уведомить пользователя: {e}")

