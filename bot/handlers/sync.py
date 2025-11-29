"""Обработчик синхронизации"""
import asyncio
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from bot.states.sync_state import SyncState
from bot.config import CITIES, CITY_MAPPING
from bot.keyboards.sync_keyboards import (
    SyncCityCallback,
    SyncTypeCallback,
    SyncBackCallback,
    get_sync_cities_keyboard,
    get_sync_type_keyboard
)
from bot.keyboards.reply_keyboards import get_owner_menu
from src.sync_data.main_page_info import NotionPageFetcher
from src.sync_data.build_structure import NotionStructureBuilder
from src.sync_data.group import NotionGroupFetcher
from src.sync_data.students import NotionStudentsFetcher
from src.sync_data.attendance import NotionAttendanceFetcher
from src.sync_data.payments import NotionPaymentsFetcher
from src.sync_data.full_sync import full_city_sync, full_all_cities_sync
from src.config import CITIES as NOTION_CITIES  # Английские названия для Notion
from bot.services.role_storage import RoleStorage
from bot.services.action_logger import ActionLogger

router = Router()
role_storage = RoleStorage()
action_logger = ActionLogger()


async def sync_structure(city_en: str) -> bool:
    """Всегда синхронизирует структуру"""
    try:
        structure_builder = NotionStructureBuilder(city_en)
        await structure_builder.build_structure()
        return True
    except Exception as e:
        print(f"❌ Ошибка синхронизации структуры для {city_en}: {e}")
        return False


async def sync_attendance(city_en: str) -> bool:
    """Синхронизирует посещаемость"""
    try:
        attendance_fetcher = NotionAttendanceFetcher(city_en)
        await attendance_fetcher.build_attendance()
        return True
    except Exception as e:
        print(f"❌ Ошибка синхронизации посещаемости для {city_en}: {e}")
        return False


async def sync_payments(city_en: str) -> bool:
    """Синхронизирует оплаты"""
    try:
        payments_fetcher = NotionPaymentsFetcher(city_en)
        await payments_fetcher.build_payments()
        return True
    except Exception as e:
        print(f"❌ Ошибка синхронизации оплат для {city_en}: {e}")
        return False


async def sync_groups(city_en: str) -> bool:
    """Синхронизирует группы"""
    try:
        group_fetcher = NotionGroupFetcher(city_en)
        await group_fetcher.save_groups_to_file()
        return True
    except Exception as e:
        print(f"❌ Ошибка синхронизации групп для {city_en}: {e}")
        return False


async def sync_main_info(city_en: str) -> bool:
    """Синхронизирует главную информацию"""
    try:
        page_fetcher = NotionPageFetcher(city_en)
        await page_fetcher.save_info_to_file()
        return True
    except Exception as e:
        print(f"❌ Ошибка синхронизации главной информации для {city_en}: {e}")
        return False


async def sync_full_city(city_en: str) -> bool:
    """Полная синхронизация города"""
    try:
        await full_city_sync(city_en)
        return True
    except Exception as e:
        print(f"❌ Ошибка полной синхронизации для {city_en}: {e}")
        return False


@router.message(F.text == "Синхронизация")
async def cmd_sync(message: Message, state: FSMContext, user_role: str = None):
    """Обработчик кнопки 'Синхронизация'"""
    # Проверяем права доступа (только владелец)
    if user_role != "owner":
        await message.answer("❌ Синхронизация доступна только для владельца")
        return
    
    await message.answer(
        "🔄 Синхронизация\n\n"
        "Выберите город или 'Все города' для полной синхронизации:",
        reply_markup=get_sync_cities_keyboard()
    )
    await state.set_state(SyncState.waiting_city)


@router.callback_query(SyncCityCallback.filter(), SyncState.waiting_city)
async def process_sync_city(
    callback: CallbackQuery,
    callback_data: SyncCityCallback,
    state: FSMContext
):
    """Обработка выбора города при синхронизации"""
    city = callback_data.city
    
    # Если выбраны все города - запускаем полную синхронизацию
    if city == "all":
        await callback.message.edit_text("⏳ Начинаю полную синхронизацию всех городов...")
        await callback.answer()
        
        # Запускаем синхронизацию в фоне
        asyncio.create_task(sync_all_cities_task(callback.message))
        await state.clear()
        return
    
    # Сохраняем выбранный город
    await state.update_data(selected_city=city)
    await state.set_state(SyncState.waiting_sync_type)
    
    await callback.message.edit_text(
        f"🔄 Синхронизация\n\n"
        f"🏙️ Город: {city}\n\n"
        f"Выберите тип синхронизации:",
        reply_markup=get_sync_type_keyboard()
    )
    await callback.answer()


@router.callback_query(SyncTypeCallback.filter(), SyncState.waiting_sync_type)
async def process_sync_type(
    callback: CallbackQuery,
    callback_data: SyncTypeCallback,
    state: FSMContext
):
    """Обработка выбора типа синхронизации"""
    sync_type = callback_data.sync_type
    data = await state.get_data()
    city = data.get("selected_city")
    
    if not city:
        await callback.answer("❌ Ошибка: город не выбран", show_alert=True)
        await state.clear()
        return
    
    # Преобразуем русское название города в английское
    city_en = CITY_MAPPING.get(city, city)
    
    # Определяем название типа синхронизации
    sync_type_names = {
        "attendance": "Посещаемость",
        "payments": "Оплаты",
        "groups": "Группы",
        "main_info": "Главная информация",
        "full": "Полная синхронизация"
    }
    sync_name = sync_type_names.get(sync_type, sync_type)
    
    await callback.message.edit_text(
        f"⏳ Синхронизация {sync_name.lower()} для города {city}...\n\n"
        f"Пожалуйста, подождите..."
    )
    await callback.answer()
    
    # Выполняем выбранный тип синхронизации
    success = False
    
    if sync_type == "full":
        # Для полной синхронизации структура уже синхронизируется внутри full_city_sync
        success = await sync_full_city(city_en)
    else:
        # Для всех остальных типов всегда синхронизируем структуру первой
        structure_success = await sync_structure(city_en)
        if not structure_success:
            await callback.message.edit_text(
                f"❌ Ошибка при синхронизации структуры для города {city}.\n"
                f"Синхронизация прервана."
            )
            await state.clear()
            return
        
        # Выполняем выбранный тип синхронизации
        if sync_type == "attendance":
            success = await sync_attendance(city_en)
        elif sync_type == "payments":
            success = await sync_payments(city_en)
        elif sync_type == "groups":
            success = await sync_groups(city_en)
        elif sync_type == "main_info":
            success = await sync_main_info(city_en)
    
    if success:
        # Логируем действие
        user_data = role_storage.get_user(callback.from_user.id)
        action_logger.log_action(
            user_id=callback.from_user.id,
            user_fio=user_data.get("fio", callback.from_user.full_name) if user_data else callback.from_user.full_name,
            username=callback.from_user.username or "нет",
            action_type="sync_data",
            action_details={
                "sync_type": sync_type,
                "city": city
            },
            city=city,
            role=user_data.get("role") if user_data else None
        )
        
        await callback.message.edit_text(
            f"✅ Синхронизация {sync_name.lower()} для города {city} завершена успешно!"
        )
    else:
        await callback.message.edit_text(
            f"❌ Ошибка при синхронизации {sync_name.lower()} для города {city}.\n"
            f"Проверьте логи для подробностей."
        )
    
    await state.clear()


async def sync_all_cities_task(message: Message):
    """Задача для синхронизации всех городов"""
    try:
        await full_all_cities_sync()
        await message.answer("✅ Полная синхронизация всех городов завершена успешно!")
    except Exception as e:
        await message.answer(
            f"❌ Ошибка при полной синхронизации всех городов.\n"
            f"Ошибка: {str(e)}"
        )


@router.callback_query(SyncBackCallback.filter())
async def process_sync_back(
    callback: CallbackQuery,
    state: FSMContext
):
    """Обработка кнопки 'Назад' или 'Отмена'"""
    current_state = await state.get_state()
    state_str = str(current_state) if current_state else ""
    
    # Если в состоянии выбора типа синхронизации - возвращаемся к выбору города
    if "waiting_sync_type" in state_str:
        await callback.message.edit_text(
            "🔄 Синхронизация\n\n"
            "Выберите город или 'Все города' для полной синхронизации:",
            reply_markup=get_sync_cities_keyboard()
        )
        await callback.answer()
        await state.set_state(SyncState.waiting_city)
        return
    
    # Если в состоянии выбора города - отменяем
    if "waiting_city" in state_str:
        await callback.message.edit_text("❌ Синхронизация отменена")
        await callback.answer("Отменено")
        await state.clear()
        return
    
    # По умолчанию - очищаем состояние
    await callback.answer("Отменено")
    await state.clear()

