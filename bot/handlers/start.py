"""Обработчик команды /start и регистрации"""
from aiogram import Router
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command, StateFilter
from bot.states.register_state import RegisterState
from bot.services.role_storage import RoleStorage
from bot.keyboards.reply_keyboards import (
    get_owner_menu,
    get_manager_menu,
    get_teacher_menu,
    get_smm_menu
)
from bot.config import OWNER_ID, CITIES
from bot.keyboards.inline_keyboards import get_role_keyboard

router = Router()
storage = RoleStorage()


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext, user_role: str = None):
    """Обработчик команды /start"""
    user_id = message.from_user.id
    username = message.from_user.username or ""
    
    # Проверяем, зарегистрирован ли пользователь
    if user_role is None:
        # Пользователь не зарегистрирован - начинаем FSM
        await message.answer(
            "👋 Добро пожаловать!\n\n"
            "Для начала работы необходимо пройти регистрацию.\n"
            "Введите ваше ФИО полностью:"
        )
        await state.set_state(RegisterState.waiting_fio)
        return
    
    # Если роль "pending" - заявка на рассмотрении
    if user_role == "pending":
        await message.answer(
            "⏳ Ваша заявка на регистрацию находится на рассмотрении у владельца.\n"
            "Ожидайте назначения роли."
        )
        return
    
    # Пользователь уже зарегистрирован - показываем меню
    await show_main_menu(message, user_role)


@router.message(StateFilter(RegisterState.waiting_fio))
async def process_fio(message: Message, state: FSMContext):
    """Обработка ввода ФИО"""
    fio = message.text.strip()
    
    if len(fio) < 3:
        await message.answer("❌ ФИО слишком короткое. Введите полное ФИО:")
        return
    
    user_id = message.from_user.id
    username = message.from_user.username or ""
    
    # Сохраняем временные данные в roles.json с ролью "pending"
    # Это позволит владельцу видеть данные при назначении роли
    storage.add_user(
        user_id=user_id,
        fio=fio,
        username=username,
        role="pending",
        city=""
    )
    
    # Отправляем запрос владельцу
    from bot.config import BOT_TOKEN
    from aiogram import Bot
    
    bot = Bot(token=BOT_TOKEN)
    
    try:
        request_text = (
            f"🔔 Новый сотрудник хочет зарегистрироваться:\n\n"
            f"ID: <code>{user_id}</code>\n"
            f"Username: @{username}\n"
            f"ФИО: {fio}"
        )
        
        await bot.send_message(
            chat_id=OWNER_ID,
            text=request_text,
            reply_markup=get_role_keyboard(user_id),
            parse_mode="HTML"
        )
        
        await message.answer(
            "✅ Ваша заявка отправлена владельцу на рассмотрение.\n"
            "Ожидайте назначения роли."
        )
        
        await state.clear()
    except Exception as e:
        await message.answer(
            f"❌ Произошла ошибка при отправке заявки. Попробуйте позже."
        )
        print(f"Ошибка отправки заявки владельцу: {e}")
    finally:
        await bot.session.close()


async def show_main_menu(message: Message, user_role: str):
    """Показывает главное меню в зависимости от роли"""
    if user_role == "owner":
        await message.answer(
            "👑 Добро пожаловать, владелец!",
            reply_markup=get_owner_menu()
        )
    elif user_role == "manager":
        await message.answer(
            "👨‍💼 Добро пожаловать, менеджер!",
            reply_markup=get_manager_menu()
        )
    elif user_role == "teacher":
        user_data = storage.get_user(message.from_user.id)
        city = user_data.get("city", "") if user_data else ""
        await message.answer(
            f"👨‍🏫 Добро пожаловать, преподаватель!\n"
            f"Ваш город: {city}",
            reply_markup=get_teacher_menu()
        )
    elif user_role == "smm":
        await message.answer(
            "📱 Добро пожаловать, SMM!",
            reply_markup=get_smm_menu()
        )
    else:
        await message.answer("❌ Неизвестная роль. Обратитесь к администратору.")

