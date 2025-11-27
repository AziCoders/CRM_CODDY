import json
from pathlib import Path
from statistics import mean

def load_json(path: Path):
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def build_city_report(city_name: str) -> dict:
    base = Path(f"../data/{city_name}")

    groups = load_json(base / "groups.json")
    students = load_json(base / "students.json")
    attendance = load_json(base / "attendance.json")
    payments = load_json(base / "payments.json")
    main_info = load_json(base / "main_page_info.json")

    report = {
        "city": base.name,
        "info": main_info,
        "groups_count": len(groups),
        "total_students": 0,
        "groups": [],
        "avg_attendance_percent_city": 0,
        "avg_payment_percent_city": 0,
    }

    attendance_percents = []
    payment_percents = []

    # === ПРОХОД ПО ГРУППАМ ===
    for group_id, group_data in groups.items():

        group_name = group_data.get("Название группы")
        group_students_block = students.get(group_id, {})
        group_attendance_block = attendance.get(group_id, {})
        group_payment_block = payments.get("payments", [])

        # список учеников
        student_list = group_students_block.get("students", [])
        total_group_students = group_students_block.get("total_students", 0)
        report["total_students"] += total_group_students

        # посещаемость
        attendance_records = group_attendance_block.get("attendance", [])
        attendance_fields = group_attendance_block.get("fields", [])[2:]  # даты
        total_lessons = len(attendance_fields)

        if total_lessons > 0 and total_group_students > 0:
            visited = 0
            for rec in attendance_records:
                visited += sum(1 for f in attendance_fields if rec.get(f) == "Был")

            attendance_percent = round((visited / (total_lessons * total_group_students)) * 100, 2)
        else:
            attendance_percent = 0

        attendance_percents.append(attendance_percent)

        # оплата
        group_payment_by_names = {p["ФИО"].lower(): p for p in group_payment_block}
        paid_count = 0

        for st in student_list:
            fio = st["ФИО"].strip().lower()
            p = group_payment_by_names.get(fio)
            if not p:
                continue

            # считает статус текущего месяца, можно расширить
            statuses = [v for k, v in p.items() if k not in ("ID", "ФИО", "Phone", "Дата оплаты",
                                                             "Комментарий", "payment_url",
                                                             "student_id", "student_url")]
            if "Оплатил" in statuses:
                paid_count += 1

        payment_percent = round((paid_count / total_group_students) * 100, 2) if total_group_students else 0
        payment_percents.append(payment_percent)

        # Добавляем группу в отчёт
        report["groups"].append({
            "group_name": group_name,
            "total_students": total_group_students,
            "students": [st["ФИО"] for st in student_list],
            "attendance_percent": attendance_percent,
            "payment_percent": payment_percent,
            "total_lessons": total_lessons,
            "attendance_records": len(attendance_records),
        })

    # === ИТОГИ ПО ГОРОДУ ===
    if attendance_percents:
        report["avg_attendance_percent_city"] = round(mean(attendance_percents), 2)

    if payment_percents:
        report["avg_payment_percent_city"] = round(mean(payment_percents), 2)

    return report


# === Пример использования ===
if __name__ == "__main__":
    city = "Nazran"
    result = build_city_report(city)

    print(json.dumps(result, ensure_ascii=False, indent=4))
