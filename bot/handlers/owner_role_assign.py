"""Обработчики для назначения ролей владельцем"""
from aiogram import Router, Bot
from aiogram.types import CallbackQuery, Message
from aiogram.filters import StateFilter
from bot.services.role_storage import RoleStorage
from bot.keyboards.inline_keyboards import (
    RoleCallback,
    CityCallback,
    get_city_keyboard
)
from bot.keyboards.reply_keyboards import (
    get_manager_menu,
    get_teacher_menu,
    get_smm_menu
)
from bot.config import OWNER_ID, BOT_TOKEN
from bot.services.action_logger import ActionLogger

router = Router()
storage = RoleStorage()
action_logger = ActionLogger()


@router.callback_query(RoleCallback.filter())
async def process_role_selection(
    callback: CallbackQuery,
    callback_data: RoleCallback,
    bot: Bot
):
    """Обработка выбора роли владельцем"""
    if callback.from_user.id != OWNER_ID:
        await callback.answer("❌ У вас нет прав для этого действия", show_alert=True)
        return
    
    user_id = callback_data.user_id
    role = callback_data.role
    
    # Получаем данные пользователя из хранилища
    user_data = storage.get_user(user_id)
    
    if not user_data:
        await callback.answer("❌ Данные пользователя не найдены", show_alert=True)
        return
    
    fio = user_data.get("fio", "")
    username = user_data.get("username", "")
    
    # Проверяем, что пользователь в статусе "pending"
    # Если роль не pending, пропускаем - пусть обрабатывает role_management
    current_role = user_data.get("role", "")
    if current_role != "pending":
        return  # Пропускаем для обработки в role_management
    
    if role == "teacher":
        # Для преподавателя нужно выбрать город
        await callback.message.edit_text(
            f"Выберите город для преподавателя:\n\n"
            f"ФИО: {fio}\n"
            f"Username: @{username}",
            reply_markup=get_city_keyboard(user_id)
        )
        await callback.answer()
    elif role in ["manager", "smm"]:
        # Для менеджера и SMM сразу сохраняем с city="all"
        try:
            storage.add_user(
                user_id=user_id,
                fio=fio,
                username=username,
                role=role,
                city="all"
            )
            
            # Логируем действие
            owner_data = storage.get_user(callback.from_user.id)
            action_logger.log_action(
                user_id=callback.from_user.id,
                user_fio=owner_data.get("fio", "Владелец") if owner_data else "Владелец",
                username=callback.from_user.username or "нет",
                action_type="add_role",
                action_details={
                    "target_user": {
                        "id": user_id,
                        "fio": fio,
                        "username": username,
                        "role": role,
                        "city": "all"
                    }
                },
                role="owner"
            )
            
            # Уведомляем пользователя
            try:
                if role == "manager":
                    menu_text = "👨‍💼 Ваша роль назначена. Добро пожаловать!"
                    menu = get_manager_menu()
                else:  # smm
                    menu_text = "📱 Ваша роль назначена. Добро пожаловать!"
                    menu = get_smm_menu()
                
                await bot.send_message(
                    chat_id=user_id,
                    text=menu_text,
                    reply_markup=menu
                )
            except Exception as e:
                print(f"Ошибка отправки сообщения пользователю {user_id}: {e}")
            
            await callback.message.edit_text(
                f"✅ Роль '{role}' успешно назначена пользователю {fio}"
            )
            await callback.answer("✅ Роль назначена")
        except Exception as e:
            await callback.answer(f"❌ Ошибка: {e}", show_alert=True)
            print(f"Ошибка назначения роли: {e}")


@router.callback_query(CityCallback.filter())
async def process_city_selection(
    callback: CallbackQuery,
    callback_data: CityCallback,
    bot: Bot
):
    """Обработка выбора города для преподавателя"""
    if callback.from_user.id != OWNER_ID:
        await callback.answer("❌ У вас нет прав для этого действия", show_alert=True)
        return
    
    user_id = callback_data.user_id
    city = callback_data.city
    
    # Получаем данные пользователя
    user_data = storage.get_user(user_id)
    
    if not user_data:
        await callback.answer("❌ Данные пользователя не найдены", show_alert=True)
        return
    
    fio = user_data.get("fio", "")
    username = user_data.get("username", "")
    
    # Проверяем, что пользователь в статусе "pending"
    current_role = user_data.get("role", "")
    if current_role != "pending":
        return  # Пропускаем для обработки в role_management
    
    try:
        # Сохраняем преподавателя с выбранным городом
        storage.add_user(
            user_id=user_id,
            fio=fio,
            username=username,
            role="teacher",
            city=city
        )
        
        # Логируем действие
        owner_data = storage.get_user(callback.from_user.id)
        action_logger.log_action(
            user_id=callback.from_user.id,
            user_fio=owner_data.get("fio", "Владелец") if owner_data else "Владелец",
            username=callback.from_user.username or "нет",
            action_type="add_role",
            action_details={
                "target_user": {
                    "id": user_id,
                    "fio": fio,
                    "username": username,
                    "role": "teacher",
                    "city": city
                }
            },
            city=city,
            role="owner"
        )
        
        # Уведомляем пользователя
        try:
            await bot.send_message(
                chat_id=user_id,
                text=f"👨‍🏫 Ваша роль назначена. Добро пожаловать!\n"
                     f"Ваш город: {city}",
                reply_markup=get_teacher_menu()
            )
        except Exception as e:
            print(f"Ошибка отправки сообщения пользователю {user_id}: {e}")
        
        await callback.message.edit_text(
            f"✅ Преподаватель '{fio}' назначен в город '{city}'"
        )
        await callback.answer("✅ Роль назначена")
    except Exception as e:
        await callback.answer(f"❌ Ошибка: {e}", show_alert=True)
        print(f"Ошибка назначения роли: {e}")

