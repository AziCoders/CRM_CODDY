import asyncio
import time

from src.config import CITIES, close_notion_client
from src.sync_data.main_page_info import NotionPageFetcher
from src.sync_data.build_structure import NotionStructureBuilder
from src.sync_data.group import NotionGroupFetcher
from src.sync_data.students import NotionStudentsFetcher
from src.sync_data.attendance import NotionAttendanceFetcher
from src.sync_data.payments import NotionPaymentsFetcher


async def full_city_sync(city: str):
    """Полная синхронизация данных по конкретному городу"""
    print(f"\n==============================")
    print(f"🚀 Начинаю синхронизацию города: {city}")
    print(f"==============================\n")

    try:
        # 1️⃣ Главная страница
        await NotionPageFetcher(city).save_info_to_file()

        # 2️⃣ Таблица групп
        group_fetcher = NotionGroupFetcher(city)
        await group_fetcher.save_groups_to_file()

        # 3️⃣ Структура групп
        structure_builder = NotionStructureBuilder(city)
        await structure_builder.build_structure()

        # 4️⃣ Ученики
        students_fetcher = NotionStudentsFetcher(city)
        await students_fetcher.build_students()

        # 5️⃣ Посещаемость
        attendance_fetcher = NotionAttendanceFetcher(city)
        await attendance_fetcher.build_attendance()

        # 6️⃣ Оплаты
        payments_fetcher = NotionPaymentsFetcher(city)
        await payments_fetcher.build_payments()

        print(f"\n✅ Синхронизация завершена для города: {city}\n")

    except Exception as e:
        print(f"❌ Ошибка при синхронизации города {city}: {e}")


async def full_all_cities_sync():
    """Запускает полную синхронизацию для всех городов"""
    print(f"🌍 Готов к синхронизации по городам: {', '.join(CITIES)}")

    start_time = time.time()

    # Parallel execution
    tasks = [full_city_sync(city) for city in CITIES]
    await asyncio.gather(*tasks)

    end_time = time.time()

    print(f"\n⏱️ Полная синхронизация завершена за {round(end_time - start_time, 2)} секунд.")

    # Close the shared client at the very end
    await close_notion_client()


if __name__ == "__main__":
    asyncio.run(full_all_cities_sync())
