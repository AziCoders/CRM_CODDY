# sync_city.py
import asyncio
import time

from main_page_info import NotionPageFetcher
from build_structure import NotionStructureBuilder
from group import NotionGroupFetcher
from students import NotionStudentsFetcher
from attendance import NotionAttendanceFetcher
from payments import NotionPaymentsFetcher


async def full_city_sync(city_name: str):
    print(f"\n🌆 === Синхронизация данных для города: {city_name.capitalize()} ===\n")

    # 1️⃣ Главная страница
    print("1️⃣ Получаем основную информацию о городе...")
    page_fetcher = NotionPageFetcher(city_name)
    await page_fetcher.save_info_to_file()

    # 2️⃣ Структура групп
    print("\n2️⃣ Формируем структуру групп...")
    group_fetcher = NotionGroupFetcher(city_name)
    await group_fetcher.save_groups_to_file()

    builder = NotionStructureBuilder(city_name)
    await builder.build_structure()

    # 3️⃣ Ученики
    print("\n3️⃣ Загружаем данные учеников...")
    students_fetcher = NotionStudentsFetcher(city_name)
    await students_fetcher.build_students()

    # 4️⃣ Посещаемость
    print("\n4️⃣ Загружаем посещаемость...")
    attendance_fetcher = NotionAttendanceFetcher(city_name)
    await attendance_fetcher.build_attendance()

    # 5️⃣ Оплаты
    print("\n5️⃣ Загружаем оплаты...")
    payments_fetcher = NotionPaymentsFetcher(city_name)
    await payments_fetcher.build_payments()

    print(f"\n✅ Синхронизация по городу {city_name.capitalize()} завершена успешно!")


if __name__ == "__main__":
    start_time = time.time()
    city = "Nazran"  # 🔧 Замени на нужный город
    asyncio.run(full_city_sync(city))
    end_time = time.time()
    print(end_time-start_time)
