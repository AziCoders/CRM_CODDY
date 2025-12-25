"""Обработчик рассылок для владельца и менеджера"""
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter, Command
from bot.services.role_storage import RoleStorage
from bot.services.action_logger import ActionLogger
from bot.keyboards.broadcast_keyboards import (
    BroadcastCallback,
    BroadcastSelectUserCallback,
    BroadcastConfirmCallback,
    get_broadcast_main_keyboard,
    get_broadcast_users_keyboard,
    get_broadcast_confirm_keyboard
)
from bot.states.broadcast_state import BroadcastState
from bot.config import BOT_TOKEN

router = Router()
storage = RoleStorage()
action_logger = ActionLogger()


@router.message(F.text == "Рассылка")
async def cmd_broadcast(message: Message, user_role: str = None):
    """Обработчик кнопки 'Рассылка'"""
    if user_role not in ["owner", "manager"]:
        await message.answer("❌ Рассылки доступны только для владельца и менеджера")
        return
    
    await message.answer(
        "📢 <b>Рассылка сотрудникам</b>\n\n"
        "Выберите тип рассылки:",
        reply_markup=get_broadcast_main_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(BroadcastCallback.filter(F.action == "back"))
async def process_broadcast_back(callback: CallbackQuery, state: FSMContext):
    """Отмена рассылки"""
    await callback.message.edit_text("❌ Рассылка отменена")
    await callback.answer()
    await state.clear()


@router.callback_query(BroadcastCallback.filter(F.action == "all"))
async def process_broadcast_all(
    callback: CallbackQuery,
    callback_data: BroadcastCallback,
    state: FSMContext,
    user_role: str = None
):
    """Обработка выбора рассылки всем сотрудникам"""
    if user_role not in ["owner", "manager"]:
        await callback.answer("❌ У вас нет доступа", show_alert=True)
        return
    
    # Получаем всех пользователей (кроме pending)
    all_users = storage.get_all_users()
    active_users = [u for u in all_users if u.get("role") != "pending"]
    
    # Сохраняем список получателей в состояние
    await state.update_data(recipients=[u.get("user_id") for u in active_users])
    
    await callback.message.edit_text(
        f"📢 <b>Рассылка всем сотрудникам</b>\n\n"
        f"Получателей: {len(active_users)}\n\n"
        f"Отправьте текст сообщения или любой файл (фото, документ, видео и т.д.) для рассылки:",
        parse_mode="HTML"
    )
    await callback.answer()
    await state.set_state(BroadcastState.waiting_message)


@router.callback_query(BroadcastCallback.filter(F.action == "select"))
async def process_broadcast_select(
    callback: CallbackQuery,
    callback_data: BroadcastCallback,
    state: FSMContext,
    user_role: str = None
):
    """Обработка выбора выборочной рассылки"""
    if user_role not in ["owner", "manager"]:
        await callback.answer("❌ У вас нет доступа", show_alert=True)
        return
    
    # Получаем всех пользователей (кроме pending)
    all_users = storage.get_all_users()
    active_users = [u for u in all_users if u.get("role") != "pending"]
    
    if not active_users:
        await callback.message.edit_text(
            "❌ Нет активных сотрудников для рассылки",
            reply_markup=get_broadcast_main_keyboard()
        )
        await callback.answer()
        return
    
    # Инициализируем состояние с пустым списком выбранных
    await state.update_data(selected_users=[], page=0)
    
    page = 0
    selected_users = []
    
    await callback.message.edit_text(
        f"👥 <b>Выборочная рассылка</b>\n\n"
        f"Выберите получателей (нажмите на имя для выбора):\n"
        f"Выбрано: {len(selected_users)}",
        parse_mode="HTML",
        reply_markup=get_broadcast_users_keyboard(active_users, selected_users, page)
    )
    await callback.answer()


@router.callback_query(BroadcastCallback.filter(F.action.startswith("page_")))
async def process_broadcast_page(
    callback: CallbackQuery,
    callback_data: BroadcastCallback,
    state: FSMContext,
    user_role: str = None
):
    """Обработка пагинации списка пользователей"""
    if user_role not in ["owner", "manager"]:
        await callback.answer("❌ У вас нет доступа", show_alert=True)
        return
    
    try:
        page = int(callback_data.action.split("_")[-1])
    except:
        page = 0
    
    # Получаем данные из состояния
    data = await state.get_data()
    selected_users = data.get("selected_users", [])
    
    # Получаем всех пользователей
    all_users = storage.get_all_users()
    active_users = [u for u in all_users if u.get("role") != "pending"]
    
    page_size = 10
    total_pages = (len(active_users) + page_size - 1) // page_size
    
    if page < 0 or page >= total_pages:
        await callback.answer("❌ Неверная страница", show_alert=True)
        return
    
    # Сохраняем текущую страницу
    await state.update_data(page=page)
    
    await callback.message.edit_text(
        f"👥 <b>Выборочная рассылка</b>\n\n"
        f"Выберите получателей (нажмите на имя для выбора):\n"
        f"Выбрано: {len(selected_users)}",
        parse_mode="HTML",
        reply_markup=get_broadcast_users_keyboard(active_users, selected_users, page)
    )
    await callback.answer()


@router.callback_query(BroadcastSelectUserCallback.filter())
async def process_broadcast_toggle_user(
    callback: CallbackQuery,
    callback_data: BroadcastSelectUserCallback,
    state: FSMContext,
    user_role: str = None
):
    """Обработка выбора/снятия выбора пользователя"""
    if user_role not in ["owner", "manager"]:
        await callback.answer("❌ У вас нет доступа", show_alert=True)
        return
    
    user_id = callback_data.user_id
    
    # Получаем данные из состояния
    data = await state.get_data()
    selected_users = data.get("selected_users", [])
    page = data.get("page", 0)
    
    # Переключаем выбор
    if user_id in selected_users:
        selected_users.remove(user_id)
    else:
        selected_users.append(user_id)
    
    # Сохраняем обновленный список
    await state.update_data(selected_users=selected_users)
    
    # Получаем всех пользователей
    all_users = storage.get_all_users()
    active_users = [u for u in all_users if u.get("role") != "pending"]
    
    await callback.message.edit_text(
        f"👥 <b>Выборочная рассылка</b>\n\n"
        f"Выберите получателей (нажмите на имя для выбора):\n"
        f"Выбрано: {len(selected_users)}",
        parse_mode="HTML",
        reply_markup=get_broadcast_users_keyboard(active_users, selected_users, page)
    )
    await callback.answer()


@router.callback_query(BroadcastCallback.filter(F.action == "confirm"))
async def process_broadcast_confirm_select(
    callback: CallbackQuery,
    callback_data: BroadcastCallback,
    state: FSMContext,
    user_role: str = None
):
    """Подтверждение выбора получателей для выборочной рассылки"""
    if user_role not in ["owner", "manager"]:
        await callback.answer("❌ У вас нет доступа", show_alert=True)
        return
    
    # Получаем данные из состояния
    data = await state.get_data()
    selected_users = data.get("selected_users", [])
    
    if not selected_users:
        await callback.answer("❌ Выберите хотя бы одного получателя", show_alert=True)
        return
    
    # Сохраняем список получателей
    await state.update_data(recipients=selected_users)
    
    # Получаем информацию о получателях
    all_users = storage.get_all_users()
    recipients_info = [u for u in all_users if u.get("user_id") in selected_users]
    
    recipients_text = "\n".join([f"• {u.get('fio', 'N/A')}" for u in recipients_info])
    
    await callback.message.edit_text(
        f"📢 <b>Выборочная рассылка</b>\n\n"
        f"Получателей: {len(selected_users)}\n\n"
        f"<b>Получатели:</b>\n{recipients_text}\n\n"
        f"Отправьте текст сообщения или любой файл (фото, документ, видео и т.д.) для рассылки:",
        parse_mode="HTML"
    )
    await callback.answer()
    await state.set_state(BroadcastState.waiting_message)


@router.message(StateFilter(BroadcastState.waiting_message), ~Command("cancel"))
async def process_broadcast_message(
    message: Message,
    state: FSMContext,
    user_role: str = None
):
    """Обработка сообщения для рассылки (текст или медиа)"""
    if user_role not in ["owner", "manager"]:
        await message.answer("❌ У вас нет доступа")
        await state.clear()
        return
    
    # Получаем получателей из состояния
    data = await state.get_data()
    recipients = data.get("recipients", [])
    
    if not recipients:
        await message.answer("❌ Ошибка: получатели не выбраны")
        await state.clear()
        return
    
    # Определяем тип контента
    content_type = None
    file_id = None
    message_text = ""
    media_type = "text"
    
    if message.text:
        # Текстовое сообщение
        message_text = message.text.strip()
        if not message_text:
            await message.answer("❌ Сообщение не может быть пустым. Отправьте текст или файл, или /cancel для отмены")
            return
        media_type = "text"
    elif message.photo:
        # Фото
        file_id = message.photo[-1].file_id  # Берем фото наибольшего размера
        message_text = message.caption or ""
        media_type = "photo"
    elif message.document:
        # Документ
        file_id = message.document.file_id
        message_text = message.caption or ""
        media_type = "document"
    elif message.video:
        # Видео
        file_id = message.video.file_id
        message_text = message.caption or ""
        media_type = "video"
    elif message.audio:
        # Аудио
        file_id = message.audio.file_id
        message_text = message.caption or ""
        media_type = "audio"
    elif message.voice:
        # Голосовое сообщение
        file_id = message.voice.file_id
        message_text = ""
        media_type = "voice"
    elif message.video_note:
        # Видеосообщение
        file_id = message.video_note.file_id
        message_text = ""
        media_type = "video_note"
    elif message.sticker:
        # Стикер
        file_id = message.sticker.file_id
        message_text = ""
        media_type = "sticker"
    else:
        await message.answer("❌ Неподдерживаемый тип сообщения. Отправьте текст, фото, документ, видео или /cancel для отмены")
        return
    
    # Формируем описание для подтверждения
    if media_type == "text":
        preview_text = f"<b>Текст сообщения:</b>\n{message_text}"
    elif media_type == "photo":
        preview_text = f"📷 <b>Фото</b>\n{message_text if message_text else '(без подписи)'}"
    elif media_type == "document":
        doc_name = message.document.file_name or "Документ"
        preview_text = f"📄 <b>Документ:</b> {doc_name}\n{message_text if message_text else '(без подписи)'}"
    elif media_type == "video":
        preview_text = f"🎥 <b>Видео</b>\n{message_text if message_text else '(без подписи)'}"
    elif media_type == "audio":
        audio_title = message.audio.title or "Аудио"
        preview_text = f"🎵 <b>Аудио:</b> {audio_title}\n{message_text if message_text else '(без подписи)'}"
    elif media_type == "voice":
        preview_text = f"🎤 <b>Голосовое сообщение</b>"
    elif media_type == "video_note":
        preview_text = f"📹 <b>Видеосообщение</b>"
    elif media_type == "sticker":
        preview_text = f"😊 <b>Стикер</b>"
    else:
        preview_text = f"📎 <b>Медиа-файл</b>"
    
    # Показываем подтверждение
    await message.answer(
        f"📢 <b>Подтверждение рассылки</b>\n\n"
        f"Получателей: {len(recipients)}\n\n"
        f"{preview_text}\n\n"
        f"Отправить рассылку?",
        parse_mode="HTML",
        reply_markup=get_broadcast_confirm_keyboard()
    )
    
    # Сохраняем данные в состоянии
    await state.update_data(
        message_text=message_text,
        media_type=media_type,
        file_id=file_id
    )


@router.message(StateFilter(BroadcastState.waiting_message), Command("cancel"))
async def cancel_broadcast(message: Message, state: FSMContext):
    """Отмена рассылки"""
    await message.answer("❌ Рассылка отменена")
    await state.clear()


@router.callback_query(BroadcastConfirmCallback.filter())
async def process_broadcast_send(
    callback: CallbackQuery,
    callback_data: BroadcastConfirmCallback,
    state: FSMContext,
    user_role: str = None
):
    """Обработка подтверждения и отправки рассылки"""
    if user_role not in ["owner", "manager"]:
        await callback.answer("❌ У вас нет доступа", show_alert=True)
        return
    
    if callback_data.action == "cancel":
        await callback.message.edit_text("❌ Рассылка отменена")
        await callback.answer()
        await state.clear()
        return
    
    # Получаем данные из состояния
    data = await state.get_data()
    recipients = data.get("recipients", [])
    message_text = data.get("message_text", "")
    media_type = data.get("media_type", "text")
    file_id = data.get("file_id")
    
    if not recipients:
        await callback.answer("❌ Ошибка: получатели не выбраны", show_alert=True)
        await state.clear()
        return
    
    if media_type == "text" and not message_text:
        await callback.answer("❌ Ошибка: данные рассылки не найдены", show_alert=True)
        await state.clear()
        return
    
    if media_type != "text" and not file_id:
        await callback.answer("❌ Ошибка: файл не найден", show_alert=True)
        await state.clear()
        return
    
    # Отправляем сообщения
    success_count = 0
    failed_count = 0
    
    await callback.message.edit_text("📤 Отправка рассылки...")
    
    # Получаем данные об отправителе
    sender_data = storage.get_user(callback.from_user.id)
    sender_fio = sender_data.get("fio", "Администратор") if sender_data else "Администратор"
    sender_role = sender_data.get("role", user_role) if sender_data else user_role
    
    # Иконки ролей
    role_icons = {
        "owner": "👤",
        "manager": "🗒",
        "teacher": "👨‍🏫",
        "smm": "📱"
    }
    role_icon = role_icons.get(sender_role, "👤")
    
    # Названия ролей
    role_names = {
        "owner": "Владелец",
        "manager": "Менеджер",
        "teacher": "Преподаватель",
        "smm": "SMM"
    }
    role_name = role_names.get(sender_role, sender_role)
    
    # Создаем экземпляр бота для отправки сообщений
    bot = Bot(token=BOT_TOKEN)
    try:
        # Формируем заголовок для рассылки с информацией об отправителе
        header_text = f"📢 <b>Рассылка от {role_icon} {sender_fio}</b>"
        if message_text:
            full_text = f"{header_text}\n\n{message_text}"
        else:
            full_text = header_text
        
        # Для медиа без подписи используем только заголовок
        text_for_caption = full_text if message_text or media_type == "text" else header_text
        
        for user_id in recipients:
            try:
                if media_type == "text":
                    # Текстовое сообщение
                    await bot.send_message(
                        chat_id=user_id,
                        text=full_text,
                        parse_mode="HTML"
                    )
                elif media_type == "photo":
                    # Фото
                    await bot.send_photo(
                        chat_id=user_id,
                        photo=file_id,
                        caption=full_text,
                        parse_mode="HTML"
                    )
                elif media_type == "document":
                    # Документ
                    await bot.send_document(
                        chat_id=user_id,
                        document=file_id,
                        caption=full_text,
                        parse_mode="HTML"
                    )
                elif media_type == "video":
                    # Видео
                    await bot.send_video(
                        chat_id=user_id,
                        video=file_id,
                        caption=full_text,
                        parse_mode="HTML"
                    )
                elif media_type == "audio":
                    # Аудио
                    await bot.send_audio(
                        chat_id=user_id,
                        audio=file_id,
                        caption=full_text,
                        parse_mode="HTML"
                    )
                elif media_type == "voice":
                    # Голосовое сообщение
                    await bot.send_voice(
                        chat_id=user_id,
                        voice=file_id,
                        caption=text_for_caption,
                        parse_mode="HTML"
                    )
                elif media_type == "video_note":
                    # Видеосообщение (не поддерживает подпись)
                    await bot.send_video_note(
                        chat_id=user_id,
                        video_note=file_id
                    )
                    # Для видеосообщений всегда отправляем текст отдельно
                    await bot.send_message(
                        chat_id=user_id,
                        text=full_text,
                        parse_mode="HTML"
                    )
                elif media_type == "sticker":
                    # Стикер (не поддерживает подпись)
                    await bot.send_sticker(
                        chat_id=user_id,
                        sticker=file_id
                    )
                    # Для стикеров всегда отправляем текст отдельно
                    await bot.send_message(
                        chat_id=user_id,
                        text=full_text,
                        parse_mode="HTML"
                    )
                
                success_count += 1
            except Exception as e:
                failed_count += 1
                print(f"Ошибка отправки сообщения пользователю {user_id}: {e}")
    finally:
        await bot.session.close()
    
    # Логируем действие (sender_data уже получен выше)
    action_details = {
        "recipients_count": len(recipients),
        "success_count": success_count,
        "failed_count": failed_count,
        "media_type": media_type
    }
    
    if message_text:
        action_details["message_preview"] = message_text[:100] + "..." if len(message_text) > 100 else message_text
    
    action_logger.log_action(
        user_id=callback.from_user.id,
        user_fio=sender_fio,
        username=callback.from_user.username or "нет",
        action_type="broadcast",
        action_details=action_details,
        role=user_role
    )
    
    await callback.message.edit_text(
        f"✅ <b>Рассылка завершена</b>\n\n"
        f"✅ Успешно отправлено: {success_count}\n"
        f"❌ Ошибок: {failed_count}",
        parse_mode="HTML"
    )
    await callback.answer("✅ Рассылка отправлена")
    await state.clear()

