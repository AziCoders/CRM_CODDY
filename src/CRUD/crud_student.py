"""
МОДУЛЬ: crud_student.py
=======================

Назначение:
-----------
Управление таблицами "Ученики" в Notion для конкретного города.

Возможности:
------------
1. Добавление ученика в конкретную группу.
2. Обновление данных ученика.
3. Удаление (архивирование) и восстановление.
4. Проверка лимита мест в классе.
5. Мягкая проверка дублей по ФИО (вариант B).
6. Автоматическое создание строки в таблице "Посещаемость"
   с использованием unique_id.number как значения в столбце "№".

После любого изменения модуль автоматически пересобирает
локальный файл students.json через NotionStudentsFetcher.
"""

import json
import os
from typing import Any, Dict, Optional, Tuple

from src.config import ROOT_DIR, get_notion_client
from src.utils import (
    build_rich_text,
    build_title,
    build_select,
    build_date,
    build_phone,
    build_number,
    build_relation,
)


class NotionStudentCRUD:
    """CRUD-класс для работы с таблицами 'Ученики' по всем группам одного города."""

    def __init__(self, city_name: str):
        self.city_name = city_name.capitalize()
        # Use shared client
        self.notion = get_notion_client()

        # === Определение путей через ROOT_DIR ===
        self.root_dir = ROOT_DIR
        self.structure_path = self.root_dir / f"data/{self.city_name}/structure.json"
        self.students_path = self.root_dir / f"data/{self.city_name}/students.json"
        self.main_info_path = self.root_dir / f"data/{self.city_name}/main_page_info.json"

        if not self.structure_path.exists():
            raise FileNotFoundError(f"❌ Файл структуры групп не найден: {self.structure_path}")

        with open(self.structure_path, "r", encoding="utf-8") as f:
            # {group_id: {"group_name": ..., "student_db_id": ..., "attendance_db_id": ...}}
            self.structure: Dict[str, Dict[str, Any]] = json.load(f)

    # ----------------------------------------------------------------------
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # ----------------------------------------------------------------------

    def _get_student_db_id(self, group_id: str) -> str:
        info = self.structure.get(group_id)
        if not info:
            raise ValueError(f"❌ Группа с id={group_id} не найдена в structure.json")

        db_id = info.get("student_db_id")
        if not db_id:
            raise ValueError(
                f"❌ У группы '{info.get('group_name')}' нет student_db_id в structure.json"
            )
        return db_id

    def _get_attendance_db_id(self, group_id: str) -> str:
        info = self.structure.get(group_id)
        if not info:
            raise ValueError(f"[ERROR] Group with id={group_id} not found in structure.json")

        db_id = info.get("attendance_db_id")
        if not db_id:
            raise ValueError(
                f"❌ У группы '{info.get('group_name')}' нет attendance_db_id в structure.json"
            )
        return db_id

    def _build_properties(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Собирает properties для создания/обновления ученика."""
        return {
            "ФИО": build_title(data.get("ФИО")),
            "Возраст": build_number(data.get("Возраст")),
            "Дата поступления": build_date(data.get("Дата поступления")),
            "Номер родителя": build_phone(data.get("Номер родителя")),
            "Имя родителя": build_rich_text(data.get("Имя родителя")),
            "Тариф": build_select(data.get("Тариф")),
            "Статус": build_select(data.get("Статус")),
            "Город": build_select(data.get("Город")),
            "Ссылка на WA, TG": build_rich_text(data.get("Ссылка на WA, TG")),
            "Комментарий": build_rich_text(data.get("Комментарий")),
            "Посещаемость": build_relation(data.get("Посещаемость")),
        }

    # ----------------------------------------------------------------------
    # ПРОВЕРКИ
    # ----------------------------------------------------------------------

    async def _check_group_capacity(self, group_id: str) -> None:
        """
        Проверяет лимит мест в классе по main_page_info.json.
        """
        if not self.main_info_path.exists():
            raise ValueError("❌ Файл main_page_info.json не найден.")

        with open(self.main_info_path, "r", encoding="utf-8") as f:
            info = json.load(f)

        seats_raw = info.get("number_seats", "")
        digits = "".join(ch for ch in seats_raw if ch.isdigit())
        if not digits:
            raise ValueError("❌ Не удалось получить число мест в классе из number_seats.")

        seats = int(digits)

        if not self.students_path.exists():
            return

        with open(self.students_path, "r", encoding="utf-8") as f:
            students_data = json.load(f)

        group_data = students_data.get(group_id, {})
        current_count = group_data.get("total_students", 0)

        if current_count >= seats:
            raise ValueError(f"❌ Лимит учеников исчерпан: {current_count}/{seats} мест занято.")

    async def _find_existing_student(
            self, group_id: str, fio: str
    ) -> Optional[Dict[str, Any]]:
        """
        Возвращает данные существующего ученика с таким ФИО
        в данной группе, если он есть. Иначе None.
        """
        if not self.students_path.exists():
            return None

        fio_norm = fio.strip().lower()

        with open(self.students_path, "r", encoding="utf-8") as f:
            students_data = json.load(f)

        group_data = students_data.get(group_id, {})
        students = group_data.get("students", [])

        for s in students:
            if s.get("ФИО", "").strip().lower() == fio_norm:
                return s

        return None

    async def _check_student_duplicate(
            self, group_id: str, fio: str
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Проверка дубля по ФИО (мягкий вариант B).
        """
        existing = await self._find_existing_student(group_id, fio)
        if existing:
            return True, existing
        return False, None

    # ----------------------------------------------------------------------
    # CRUD: ДОБАВЛЕНИЕ / ОБНОВЛЕНИЕ / УДАЛЕНИЕ
    # ----------------------------------------------------------------------

    async def add_student(
            self,
            group_id: str,
            student_data: Dict[str, Any],
            force: bool = False,
    ) -> Dict[str, Any]:
        """
        Добавляет ученика в таблицу 'Ученики' указанной группы.
        """
        # 1) Проверка лимита мест
        await self._check_group_capacity(group_id)

        # 2) Проверка дубля по ФИО (мягкий вариант B)
        is_duplicate, existing = await self._check_student_duplicate(
            group_id, student_data.get("ФИО", "")
        )

        if is_duplicate and not force:
            return {
                "duplicate": True,
                "existing_student_id": existing.get("ID"),
                "existing_student": existing,
                "message": f"Student '{student_data.get('ФИО', '')}' already exists in this group.",
            }

        # 3) Создание ученика в Notion
        student_db_id = self._get_student_db_id(group_id)
        properties = self._build_properties(student_data)

        page = await self.notion.pages.create(
            parent={"database_id": student_db_id},
            properties=properties,
        )
        student_id = page["id"]

        # 4) Получаем уникальный номер ученика (поле ID с type=unique_id)
        page_info = await self.notion.pages.retrieve(student_id)
        unique_number = page_info["properties"]["ID"]["unique_id"]["number"]
        unique_number_str = str(unique_number) if unique_number is not None else ""

        # 5) Создаём строку посещаемости
        await self._add_student_to_attendance(group_id, student_id, unique_number_str)

        # 6) Создаём запись в таблице оплат
        await self._add_student_to_payments(student_data, student_id)

        return {
            "duplicate": False,
            "student_id": student_id,
            "message": f"Student '{student_data.get('ФИО', '')}' added.",
        }

    async def _add_student_to_payments(self, student_data: Dict[str, Any], student_id: str):
        """
        Создаёт запись в таблице оплат при добавлении нового ученика.
        """
        from src.CRUD.crud_payment import NotionPaymentUpdater

        updater = NotionPaymentUpdater(self.city_name)

        # Дата поступления
        date_start = student_data.get("Дата поступления")

        # Дата оплаты = "15 числа"
        payment_date = ""
        if date_start:
            try:
                day = int(date_start.split("-")[2])
                payment_date = f"{day} числа"
            except Exception:
                payment_date = ""
        else:
            payment_date = ""

        await updater.add_student_to_payments(
            {
                "ФИО": student_data["ФИО"],
                "Номер родителя": student_data.get("Номер родителя", ""),
                "student_url": f"https://www.notion.so/{student_id.replace('-', '')}",
            },
            payment_date=payment_date
        )
        await updater.close()

    async def _add_student_to_attendance(
            self,
            group_id: str,
            student_id: str,
            number: str,
    ) -> None:
        """
        Создаёт строку в таблице 'Посещаемость' для данного ученика.
        """
        try:
            attendance_db_id = self._get_attendance_db_id(group_id)
        except ValueError as e:
            print(f"[WARN] {e}")
            return

        from src.CRUD.crud_attendance import NotionAttendanceUpdater

        updater = NotionAttendanceUpdater()

        await updater.add_student_row(
            db_id=attendance_db_id,
            student_id=student_id,
            number=number,
        )
        if hasattr(updater, 'close'):
            await updater.close()

    async def update_student(
            self,
            student_id: str,
            fields: Dict[str, Any],
    ) -> None:
        """
        Обновляет данные ученика по его ID (страницы Notion).
        """
        props: Dict[str, Any] = {}

        for key, value in fields.items():
            if key == "ФИО":
                props[key] = build_title(value)
            elif key in ("Имя родителя", "Ссылка на WA, TG", "Комментарий"):
                props[key] = build_rich_text(value)
            elif key in ("Тариф", "Статус", "Город"):
                props[key] = build_select(value)
            elif key == "Номер родителя":
                props[key] = build_phone(value)
            elif key == "Возраст":
                props[key] = build_number(value)
            elif key == "Дата поступления":
                props[key] = build_date(value)
            elif key == "Посещаемость":
                props[key] = build_relation(value)

        if not props:
            return

        await self.notion.pages.update(page_id=student_id, properties=props)

    async def delete_student(self, student_id: str, reason: str, group_id: str = None) -> Dict[str, Any]:
        """
        Переносит ученика в таблицу 'Ушедшие ученики',
        удаляет из посещаемости и оплат,
        устанавливает статус 'Не обучается',
        записывает пользовательский комментарий (reason),
        и архивирует запись в основной таблице.
        
        Returns:
            Dict с результатами операций:
            {
                "added_to_left": bool,
                "archived_from_students": bool,
                "deleted_from_attendance": bool,
                "deleted_from_payments": bool,
                "errors": List[str]
            }
        """
        from src.CRUD.crud_attendance import NotionAttendanceUpdater
        from src.CRUD.crud_payment import NotionPaymentUpdater

        result = {
            "added_to_left": False,
            "archived_from_students": False,
            "deleted_from_attendance": False,
            "deleted_from_payments": False,
            "errors": []
        }

        left_db_id = os.getenv("LEFT_STUDENTS_DB_ID")
        if not left_db_id:
            result["errors"].append("❌ В .env отсутствует LEFT_STUDENTS_DB_ID")
            return result

        try:
            # === 1. Загружаем страницу ученика ===
            page = await self.notion.pages.retrieve(student_id)
            props = page["properties"]

            fio = props["ФИО"]["title"][0]["plain_text"] if props["ФИО"]["title"] else ""
            phone = props["Номер родителя"]["phone_number"] if props["Номер родителя"].get("phone_number") else ""
            parent_name = props["Имя родителя"]["rich_text"][0]["plain_text"] if props["Имя родителя"]["rich_text"] else ""
            city = props["Город"]["select"]["name"] if props["Город"]["select"] else ""
            tarif = props["Тариф"]["select"]["name"] if props["Тариф"]["select"] else ""
            date_start = props["Дата поступления"]["date"]["start"] if props["Дата поступления"]["date"] else None
            age = props["Возраст"]["number"] if props["Возраст"].get("number") else None
            # Обрабатываем поле "Ссылка на WA, TG"
            link_wa_tg_prop = props.get("Ссылка на WA, TG", {})
            if link_wa_tg_prop and link_wa_tg_prop.get("rich_text"):
                link_wa_tg = build_rich_text(link_wa_tg_prop["rich_text"][0]["plain_text"] if link_wa_tg_prop["rich_text"] else "")
            else:
                link_wa_tg = build_rich_text("")

            # === 2. Вытащим название группы из students.json ===
            group_name = ""
            found_group_id = None
            if self.students_path.exists():
                with open(self.students_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for gid, group in data.items():
                        for st in group.get("students", []):
                            if st["ID"] == student_id:
                                group_name = group.get("group_name", "")
                                found_group_id = gid
                                break
                        if found_group_id:
                            break

            # Используем переданный group_id или найденный
            if not found_group_id and group_id:
                found_group_id = group_id

            # === 3. Формируем properties для таблицы ушедших ===
            # Статус — всегда "Не обучается"
            left_props = {
                "ФИО": build_title(fio),
                "Возраст": build_number(age) if age else None,
                "Номер родителя": build_phone(phone) if phone else None,
                "Имя родителя": build_rich_text(parent_name),
                "Город": build_select(city) if city else None,
                "Тариф": build_select(tarif) if tarif else None,
                "Дата поступления": build_date(date_start) if date_start else None,
                "Группа": build_rich_text(group_name),
                "Ссылка на WA, TG": link_wa_tg,
                "Комментарий": build_rich_text(reason),  # 🔥 пользовательский комментарий
                "Статус": build_select("Не обучается"),  # 🔥 статус фиксированный
            }

            # Убираем None значения
            left_props = {k: v for k, v in left_props.items() if v is not None}

            # === 4. Создаём запись в таблице ушедших ===
            try:
                await self.notion.pages.create(
                    parent={"database_id": left_db_id},
                    properties=left_props
                )
                result["added_to_left"] = True
                print(f"✅ Ученик '{fio}' добавлен в 'Ушедшие ученики'")
            except Exception as e:
                error_msg = f"❌ Ошибка добавления в 'Ушедшие ученики': {e}"
                result["errors"].append(error_msg)
                print(error_msg)

            # === 5. Удаляем из посещаемости ===
            if found_group_id:
                try:
                    attendance_db_id = self._get_attendance_db_id(found_group_id)
                    attendance_updater = NotionAttendanceUpdater()
                    
                    # Ищем все записи посещаемости для этого ученика
                    response = await self.notion.databases.query(
                        database_id=attendance_db_id,
                        filter={
                            "property": "ФИО",
                            "relation": {"contains": student_id},
                        },
                    )
                    
                    # Архивируем все найденные записи
                    for record in response["results"]:
                        try:
                            await self.notion.pages.update(
                                page_id=record["id"],
                                archived=True
                            )
                        except Exception as e:
                            result["errors"].append(f"❌ Ошибка удаления записи посещаемости {record['id']}: {e}")
                    
                    if response["results"]:
                        result["deleted_from_attendance"] = True
                        print(f"✅ Удалено записей посещаемости: {len(response['results'])}")
                except ValueError as e:
                    # Если группа не найдена - это не критично, просто пропускаем
                    error_msg = f"⚠️ Не удалось найти группу для удаления из посещаемости: {e}"
                    result["errors"].append(error_msg)
                    print(error_msg)
                except Exception as e:
                    error_msg = f"❌ Ошибка удаления из посещаемости: {e}"
                    result["errors"].append(error_msg)
                    print(error_msg)
            else:
                # Пробуем найти группу через все группы города
                try:
                    # Ищем во всех группах города
                    for gid in self.structure.keys():
                        try:
                            attendance_db_id = self._get_attendance_db_id(gid)
                            response = await self.notion.databases.query(
                                database_id=attendance_db_id,
                                filter={
                                    "property": "ФИО",
                                    "relation": {"contains": student_id},
                                },
                            )
                            if response["results"]:
                                # Нашли группу, удаляем записи
                                for record in response["results"]:
                                    try:
                                        await self.notion.pages.update(
                                            page_id=record["id"],
                                            archived=True
                                        )
                                    except Exception as e:
                                        result["errors"].append(f"❌ Ошибка удаления записи посещаемости {record['id']}: {e}")
                                
                                result["deleted_from_attendance"] = True
                                print(f"✅ Удалено записей посещаемости: {len(response['results'])}")
                                break
                        except (ValueError, Exception):
                            continue
                except Exception as e:
                    error_msg = f"⚠️ Не удалось удалить из посещаемости: {e}"
                    result["errors"].append(error_msg)
                    print(error_msg)

            # === 6. Удаляем из оплат ===
            try:
                payment_updater = NotionPaymentUpdater(self.city_name)
                
                # Ищем записи в таблице оплат по ФИО
                fio_for_search = fio
                response = await self.notion.databases.query(
                    database_id=payment_updater.database_id,
                    filter={
                        "property": "ФИО",
                        "rich_text": {"equals": fio_for_search},
                    },
                )
                
                # Если не нашли по ФИО, пробуем по телефону
                if not response["results"] and phone:
                    phone_digits = "".join(filter(str.isdigit, phone))
                    if phone_digits:
                        response = await self.notion.databases.query(
                            database_id=payment_updater.database_id,
                            filter={
                                "property": "Phone",
                                "phone_number": {"contains": phone_digits[-10:]},
                            },
                        )
                
                # Архивируем все найденные записи
                for record in response["results"]:
                    try:
                        await self.notion.pages.update(
                            page_id=record["id"],
                            archived=True
                        )
                    except Exception as e:
                        result["errors"].append(f"❌ Ошибка удаления записи оплаты {record['id']}: {e}")
                
                if response["results"]:
                    result["deleted_from_payments"] = True
                    print(f"✅ Удалено записей оплат: {len(response['results'])}")
            except Exception as e:
                error_msg = f"❌ Ошибка удаления из оплат: {e}"
                result["errors"].append(error_msg)
                print(error_msg)

            # === 7. Удаляем ученика из основной таблицы (архивируем) ===
            try:
                await self.notion.pages.update(
                    page_id=student_id,
                    archived=True
                )
                result["archived_from_students"] = True
                print(f"✅ Ученик '{fio}' архивирован из основной таблицы")
            except Exception as e:
                error_msg = f"❌ Ошибка архивирования из основной таблицы: {e}"
                result["errors"].append(error_msg)
                print(error_msg)

            print(f"🟡 Ученик '{fio}' обработан. Результаты: {result}")
            return result

        except Exception as e:
            error_msg = f"❌ Критическая ошибка при удалении ученика: {e}"
            result["errors"].append(error_msg)
            print(error_msg)
            return result

    async def close(self):
        pass


# # -----------------------------------------------------------
# # ПОЛНЫЙ ТЕСТ ВСЕХ МЕТОДОВ МОДУЛЯ
# # -----------------------------------------------------------
# if __name__ == "__main__":
#     import asyncio
#     import random
#
#
#     async def test_crud():
#         # Используем существующий город для теста
#         city = "Karabulak"
#         print(f"--- [TEST] Testing CRUD Student for city: {city} ---")
#
#         try:
#             crud = NotionStudentCRUD(city)
#         except Exception as e:
#             print(f"[ERROR] Initialization failed: {e}")
#             return
#
#         # 1. Выбираем первую попавшуюся группу
#         if not crud.structure:
#             print("[ERROR] No groups in structure.json. Run full_sync first.")
#             return
#
#         group_id = "26ed06fc-f646-810b-8fca-e7b3a820a21a"
#         group_name = crud.structure[group_id].get("group_name", "Unknown")
#         print(f"[INFO] Selected group: {group_name} (ID: {group_id})")
#
#         # 2. Данные тестового ученика
#
#         test_fio = input("Введите ФИО: ")
#         age = int(input("Введите Возраст: "))
#         number = input("Введите Номер родителя: ")
#         new_student = {
#             "ФИО": test_fio,
#             "Возраст": age,
#             "Дата поступления": "2025-11-22",
#             "Номер родителя": number,
#             "Имя родителя": "",
#             "Тариф": "Группа 2 раза",
#             "Статус": "Обучается",
#             "Город": "Малгобек",
#             "Ссылка на WA, TG": "",
#             "Комментарий": "",
#         }
#
#         print(f"\n1. Adding student: {test_fio}...")
#         try:
#             result = await crud.add_student(group_id, new_student, force=True)
#             print(f"   Result: {result}")
#
#             if result.get("duplicate"):
#                 student_id = result.get("existing_student_id")
#                 print(f"   [WARN] Student already exists, using ID: {student_id}")
#             else:
#                 student_id = result.get("student_id")
#                 print(f"   [OK] Student created, ID: {student_id}")
#
#             if not student_id:
#                 print("[ERROR] Failed to get student ID.")
#                 return
#
#             # # 3. Обновление
#             # print(f"\n2. Updating comment...")
#             # await crud.update_student(student_id, {"Комментарий": "Updated by autotest"})
#             # print("   [OK] Comment updated.")
#             #
#             # # 4. Удаление (Архивация)
#             # print(f"\n3. Deleting (archiving)...")
#             # await crud.delete_student(student_id)
#             # print("   [OK] Student archived.")
#             #
#             # # 5. Восстановление
#             # print(f"\n4. Restoring...")
#             # await crud.restore_student(student_id)
#             # print("   [OK] Student restored.")
#
#             print(f"\n[SUCCESS] CRUD Student test completed!")
#
#         except Exception as e:
#             print(f"\n[ERROR] Test failed: {e}")
#
#
#     asyncio.run(test_crud())


# if __name__ == "__main__":
#     import asyncio
#
#     async def test_delete():
#         city = "Magas_test"   # поставь свой город
#         student_id = "26cd06fc-f646-8137-b634-c4740b537fb9"
#
#         crud = NotionStudentCRUD(city)
#
#         print("🔍 Удаляю ученика...")
#         await crud.delete_student(student_id, "Перестал посещать, не отвечает на звонки")
#
#         print("🧪 Проверяю результат...")
#
#         # 1. Проверяем, что страница ученика архивирована
#         page = await crud.notion.pages.retrieve(student_id)
#         print("   🔸 archived:", page["archived"])
#
#
#     asyncio.run(test_delete())
