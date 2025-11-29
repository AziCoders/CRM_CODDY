"""Обработчик управления ролями"""
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from bot.services.role_storage import RoleStorage
from bot.services.action_logger import ActionLogger
from bot.keyboards.role_management_keyboards import (
    RoleManagementCallback,
    RoleDeleteCallback,
    RoleEditCallback,
    get_role_management_keyboard,
    get_users_list_keyboard,
    get_user_actions_keyboard,
    get_confirm_delete_keyboard
)
from bot.keyboards.inline_keyboards import (
    RoleCallback,
    CityCallback,
    get_role_keyboard,
    get_city_keyboard
)
from bot.keyboards.reply_keyboards import get_owner_menu
from bot.config import OWNER_ID, CITIES
from bot.states.role_management_state import RoleManagementState
from aiogram.filters import StateFilter, Command

router = Router()
storage = RoleStorage()
action_logger = ActionLogger()


@router.message(F.text == "Управление ролями")
async def cmd_role_management(message: Message, user_role: str = None):
    """Обработчик кнопки 'Управление ролями'"""
    if user_role != "owner":
        await message.answer("❌ Управление ролями доступно только для владельца")
        return
    
    await message.answer(
        "👥 <b>Управление ролями</b>\n\n"
        "Выберите действие:",
        reply_markup=get_role_management_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(RoleManagementCallback.filter())
async def process_role_management(
    callback: CallbackQuery,
    callback_data: RoleManagementCallback,
    user_role: str = None
):
    """Обработка действий управления ролями"""
    if user_role != "owner":
        await callback.answer("❌ У вас нет доступа", show_alert=True)
        return
    
    action = callback_data.action
    
    if action == "back":
        await callback.message.edit_text("❌ Операция отменена")
        await callback.answer()
        return
    
    if action == "view":
        # Показываем список работников
        users = storage.get_all_users()
        
        if not users:
            await callback.message.edit_text(
                "👥 <b>Работники</b>\n\n"
                "Работники не найдены.",
                parse_mode="HTML",
                reply_markup=get_role_management_keyboard()
            )
            await callback.answer()
            return
        
        # Формируем список для отображения
        page = 0
        page_size = 10
        total_pages = (len(users) + page_size - 1) // page_size
        
        await callback.message.edit_text(
            f"👥 <b>Работники</b>\n\n"
            f"Всего работников: {len(users)}\n"
            f"Страница {page + 1} из {total_pages}\n\n"
            f"Выберите работника для просмотра:",
            parse_mode="HTML",
            reply_markup=get_users_list_keyboard(users, page, page_size)
        )
        await callback.answer()
        return
    
    if action.startswith("view_page_"):
        # Пагинация списка работников
        try:
            page = int(action.split("_")[-1])
        except:
            page = 0
        
        users = storage.get_all_users()
        page_size = 10
        total_pages = (len(users) + page_size - 1) // page_size
        
        if page < 0 or page >= total_pages:
            await callback.answer("❌ Неверная страница", show_alert=True)
            return
        
        await callback.message.edit_text(
            f"👥 <b>Работники</b>\n\n"
            f"Всего работников: {len(users)}\n"
            f"Страница {page + 1} из {total_pages}\n\n"
            f"Выберите работника для просмотра:",
            parse_mode="HTML",
            reply_markup=get_users_list_keyboard(users, page, page_size)
        )
        await callback.answer()
        return
    
    if action == "add":
        # Начинаем процесс добавления роли
        await callback.message.edit_text(
            "➕ <b>Добавление роли</b>\n\n"
            "Отправьте ID пользователя Telegram, которому хотите назначить роль.\n\n"
            "Для отмены отправьте /cancel",
            parse_mode="HTML"
        )
        await callback.answer()
        # FSM состояние будет установлено в обработчике сообщения
        return


@router.message(StateFilter(RoleManagementState.waiting_user_id), F.text, ~Command("cancel"))
async def process_add_role_user_id(message: Message, state: FSMContext, user_role: str = None, bot: Bot = None):
    """Обработка ввода ID пользователя для добавления роли"""
    if user_role != "owner":
        await message.answer("❌ У вас нет доступа")
        await state.clear()
        return
    
    try:
        user_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Неверный формат ID. Введите числовой ID пользователя или /cancel для отмены")
        return
    
    # Проверяем, существует ли пользователь в Telegram
    try:
        user_info = await bot.get_chat(user_id)
        username = user_info.username or "нет"
        full_name = user_info.full_name or "Не указано"
        
        # Сохраняем данные в состояние
        await state.update_data(
            target_user_id=user_id,
            target_username=username,
            target_full_name=full_name
        )
        
        # Проверяем, есть ли уже роль у этого пользователя
        existing_user = storage.get_user(user_id)
        if existing_user:
            await message.answer(
                f"⚠️ Пользователь уже имеет роль:\n\n"
                f"👤 ФИО: {existing_user.get('fio', 'N/A')}\n"
                f"👔 Роль: {existing_user.get('role', 'N/A')}\n"
                f"🏙️ Город: {existing_user.get('city', 'N/A')}\n\n"
                f"Выберите роль для обновления:",
                reply_markup=get_role_keyboard(user_id)
            )
        else:
            # Сохраняем пользователя с ролью "pending" для назначения
            storage.add_user(
                user_id=user_id,
                fio=full_name,
                username=username,
                role="pending",
                city=""
            )
            
            await message.answer(
                f"✅ Пользователь найден:\n\n"
                f"👤 ФИО: {full_name}\n"
                f"🆔 ID: {user_id}\n"
                f"📱 Username: @{username}\n\n"
                f"Выберите роль:",
                reply_markup=get_role_keyboard(user_id)
            )
        
        await state.set_state(RoleManagementState.waiting_role)
        await bot.session.close()
    except Exception as e:
        await message.answer(
            f"❌ Не удалось найти пользователя с ID {user_id}.\n"
            f"Убедитесь, что пользователь начал диалог с ботом.\n\n"
            f"Попробуйте снова или отправьте /cancel для отмены"
        )
        print(f"Ошибка получения информации о пользователе: {e}")
        await bot.session.close()


@router.message(StateFilter(RoleManagementState.waiting_user_id), Command("cancel"))
async def cancel_add_role(message: Message, state: FSMContext):
    """Отмена добавления роли"""
    await message.answer("❌ Добавление роли отменено")
    await state.clear()


@router.callback_query(RoleEditCallback.filter())
async def process_user_edit(
    callback: CallbackQuery,
    callback_data: RoleEditCallback,
    user_role: str = None
):
    """Обработка просмотра/редактирования пользователя"""
    if user_role != "owner":
        await callback.answer("❌ У вас нет доступа", show_alert=True)
        return
    
    user_id = callback_data.user_id
    
    # Получаем данные пользователя
    user_data = storage.get_user(user_id)
    
    if not user_data:
        await callback.answer("❌ Пользователь не найден", show_alert=True)
        return
    
    fio = user_data.get("fio", "Не указано")
    username = user_data.get("username", "нет")
    role = user_data.get("role", "N/A")
    city = user_data.get("city", "N/A")
    
    # Иконки ролей
    role_icons = {
        "owner": "👑",
        "manager": "👨‍💼",
        "teacher": "👨‍🏫",
        "smm": "📱",
        "pending": "⏳"
    }
    role_icon = role_icons.get(role, "👤")
    
    # Названия ролей
    role_names = {
        "owner": "Владелец",
        "manager": "Менеджер",
        "teacher": "Преподаватель",
        "smm": "SMM",
        "pending": "Ожидает назначения"
    }
    role_name = role_names.get(role, role)
    
    # Формируем информацию
    info_lines = [
        f"{role_icon} <b>Информация о работнике</b>",
        "",
        f"👤 <b>ФИО:</b> {fio}",
        f"🆔 <b>ID:</b> {user_id}",
        f"📱 <b>Username:</b> @{username}",
        f"👔 <b>Роль:</b> {role_name}",
    ]
    
    if city and city != "all":
        info_lines.append(f"🏙️ <b>Город:</b> {city}")
    elif city == "all":
        info_lines.append(f"🏙️ <b>Город:</b> Все города")
    
    # Не показываем кнопку удаления для владельца
    if user_id == OWNER_ID:
        await callback.message.edit_text(
            "\n".join(info_lines),
            parse_mode="HTML",
            reply_markup=get_role_management_keyboard()
        )
    else:
        await callback.message.edit_text(
            "\n".join(info_lines),
            parse_mode="HTML",
            reply_markup=get_user_actions_keyboard(user_id)
        )
    
    await callback.answer()


@router.callback_query(RoleDeleteCallback.filter())
async def process_role_delete(
    callback: CallbackQuery,
    callback_data: RoleDeleteCallback,
    user_role: str = None,
    bot: Bot = None
):
    """Обработка удаления роли"""
    if user_role != "owner":
        await callback.answer("❌ У вас нет доступа", show_alert=True)
        return
    
    user_id = callback_data.user_id
    
    # Получаем данные пользователя перед удалением
    user_data = storage.get_user(user_id)
    
    if not user_data:
        await callback.answer("❌ Пользователь не найден", show_alert=True)
        return
    
    # Проверяем, не владелец ли это
    if user_id == OWNER_ID:
        await callback.answer("❌ Нельзя удалить владельца", show_alert=True)
        return
    
    # Удаляем пользователя
    success = storage.remove_user(user_id)
    
    if success:
        # Логируем действие
        owner_data = storage.get_user(callback.from_user.id)
        action_logger.log_action(
            user_id=callback.from_user.id,
            user_fio=owner_data.get("fio", "Владелец") if owner_data else "Владелец",
            username=callback.from_user.username or "нет",
            action_type="remove_role",
            action_details={
                "target_user": {
                    "id": user_id,
                    "fio": user_data.get("fio", ""),
                    "username": user_data.get("username", ""),
                    "role": user_data.get("role", ""),
                    "city": user_data.get("city", "")
                }
            },
            role="owner"
        )
        
        await callback.message.edit_text(
            f"✅ Роль пользователя <b>{user_data.get('fio', 'N/A')}</b> успешно удалена",
            parse_mode="HTML",
            reply_markup=get_role_management_keyboard()
        )
        await callback.answer("✅ Роль удалена")
        
        # Уведомляем пользователя
        try:
            await bot.send_message(
                chat_id=user_id,
                text="❌ Ваша роль была удалена администратором."
            )
        except:
            pass
    else:
        await callback.answer("❌ Ошибка при удалении роли", show_alert=True)

