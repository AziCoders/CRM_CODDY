import json
import os
import datetime

def get_month_name(month_num):
    months = [
        "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
        "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
    ]
    if 1 <= month_num <= 12:
        return months[month_num - 1]
    return None

def generate_report(city_name, month=None):
    # Determine month if not provided
    if not month:
        current_month_num = datetime.datetime.now().month
        month = get_month_name(current_month_num)
    
    # Normalize month to Title case just in case
    month = month.capitalize()

    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    data_dir = os.path.join(base_dir, "data")

    cities_to_process = []
    if city_name.lower() == "все":
        # List all directories in data_dir
        try:
            for item in os.listdir(data_dir):
                if os.path.isdir(os.path.join(data_dir, item)):
                    cities_to_process.append(item)
        except FileNotFoundError:
            return "Ошибка: Папка с данными не найдена."
    else:
        # Check if city exists
        # We might need to handle case sensitivity or mapping. 
        # Assuming user provides correct folder name or close to it.
        # Let's try to match case-insensitive
        target_city = None
        try:
            for item in os.listdir(data_dir):
                if item.lower() == city_name.lower():
                    target_city = item
                    break
        except FileNotFoundError:
             return "Ошибка: Папка с данными не найдена."
        
        if target_city:
            cities_to_process.append(target_city)
        else:
            return f"Ошибка: Город '{city_name}' не найден."

    report_lines = []
    
    for city in cities_to_process:
        city_report = process_city(data_dir, city, month)
        report_lines.append(city_report)
        report_lines.append("\n" + "-"*20 + "\n")

    return "".join(report_lines)

def process_city(data_dir, city_name, month):
    city_path = os.path.join(data_dir, city_name)
    students_path = os.path.join(city_path, "students.json")
    payments_path = os.path.join(city_path, "payments.json")

    try:
        with open(students_path, 'r', encoding='utf-8') as f:
            students_data = json.load(f)
        with open(payments_path, 'r', encoding='utf-8') as f:
            payments_data = json.load(f)
    except FileNotFoundError:
        return f"Данные для города {city_name} не найдены (отсутствует students.json или payments.json)."
    except json.JSONDecodeError:
        return f"Ошибка чтения данных для города {city_name}."

    # Process Students
    all_students = {}
    for group_id, group_info in students_data.items():
        for student in group_info.get("students", []):
            s_id = student.get("ID")
            if s_id:
                all_students[s_id] = {
                    "name": student.get("ФИО", "Unknown"),
                    "url": student.get("student_url", ""),
                    "phone": student.get("Номер родителя", "")
                }

    # Process Payments
    # We need to filter payments by month? 
    # The structure in payments.json shows "payments_data": { "Октябрь": "Оплатил", ... }
    # So we are checking if the student has paid for the SPECIFIED month.
    
    payments_with_id = {}
    payments_without_id = []
    
    total_payments_count = 0

    for payment in payments_data.get("payments", []):
        s_id = payment.get("student_id")
        p_data_map = payment.get("payments_data", {})
        
        # Check status for the requested month
        status = p_data_map.get(month)
        
        # What counts as "paid"? "Оплатил"?
        # Or does the mere existence of the record mean we should check it?
        # The prompt says "show how many people are in the payments table".
        # But usually we want to know who hasn't paid for the specific month.
        # However, the previous script just checked if the student ID exists in the payments list AT ALL.
        # But now we have a month context.
        # If I look at the previous script, it didn't filter by month. It just checked if `s_id` is in `payments_data`.
        # But `payments_data` is a list of payment records.
        # Each record seems to represent a student's payment history?
        # Let's re-read the structure.
        # "payments": [ { "ID": "...", "payments_data": { "Октябрь": "Оплатил", "Ноябрь": "Написали" } } ]
        # So one record per student in the payments file.
        # So "Missing in payments" means no record at all for this student in payments.json.
        # BUT the user asked for "report for [Month]".
        # Maybe they mean "Who hasn't paid for [Month]"?
        # "показывать кого нет и где его нет" - "show who is missing and where".
        # In the example: "Someone is missing in payments".
        # If I add month logic, it probably means:
        # 1. Student exists in students.json but NOT in payments.json (Global missing)
        # 2. Student exists in payments.json but status for [Month] is NOT "Оплатил"?
        # The user said: "name of report, city and month... form a report for this city and in this month".
        # If I strictly follow the previous script logic, it only checked for existence of the record.
        # But the new requirement mentions month.
        # If I look at the example output again: "Someone is missing in payments".
        # It doesn't explicitly say "Didn't pay for November".
        # But why ask for month if we don't use it?
        # Let's assume we need to check the STATUS for that month.
        # If status is "Оплатил", they are good.
        # If status is empty, "Написали", "Не оплатил" -> they are "missing payment"?
        # OR maybe the user just wants to filter the "Missing in payments" list? No, that doesn't make sense.
        # Let's assume "Missing in payments" means:
        # A) No record in payments.json OR
        # B) Record exists but [Month] is not "Оплатил".
        
        # Let's stick to the previous logic for "Missing in payments" (No record) first, 
        # and maybe add a section "Not paid for [Month]"?
        # Or maybe "Missing in payments" implies "No payment record for this month"?
        # But the structure is one record per student with multiple months.
        
        # Let's look at the user prompt again: "отчет по оплатам Назрань ноябрь".
        # "show how many people are in the payments table and how many people are there in total... show who is missing".
        # If I specify November, I probably care about November payments.
        
        # Let's refine the logic:
        # 1. "Missing in payments": Student is in students.json. 
        #    Check if they have a record in payments.json AND that record has "Оплатил" for [Month].
        #    If not, they are "missing".
        
        # Wait, the previous script output "Missing in payments" for students who had NO record in payments.json.
        # It didn't check the content of `payments_data`.
        # If I strictly follow "Missing in payments", it means the record is absent.
        # But if I add month, I should probably check the status.
        
        # Let's try to be smart.
        # If the user specifies a month, they likely want to know who hasn't paid for that month.
        # So I will list students who:
        # 1. Don't have a record in payments.json.
        # 2. Have a record but `payments_data[month]` is not "Оплатил".
        
        # Let's verify what the user meant by "Missing in payments".
        # In the previous turn, the user accepted the script that only checked for ID existence.
        # But now they added "Month".
        
        # I will implement:
        # List 1: "Не оплатили за [Month]" (Didn't pay for [Month])
        # This includes:
        #   - Students not in payments.json at all.
        #   - Students in payments.json but status for [Month] != "Оплатил".
        
        # List 2: "Missing in students" (Unrecognized payment)
        #   - Payment record exists (and maybe has "Оплатил" for [Month]?) but no student ID match.
        
        # Let's look at the example output in the FIRST request:
        # "Кто-то отсутствуетс в оплатах"
        
        # I will combine them.
        
        p_record = {
             "name": payment.get("ФИО", "Unknown"),
             "url": payment.get("payment_url", ""),
             "phone": payment.get("Phone", ""),
             "status": status
        }
        
        if s_id:
            payments_with_id[s_id] = p_record
        else:
            payments_without_id.append(p_record)

    # Comparison
    not_paid_list = []
    
    for s_id, s_data in all_students.items():
        if s_id not in payments_with_id:
            # Case 1: No record in payments.json
            s_data['reason'] = "Нет записи в таблице оплат"
            not_paid_list.append(s_data)
        else:
            # Case 2: Record exists, check month status
            p_rec = payments_with_id[s_id]
            status = p_rec.get('status')
            if status != "Оплатил":
                 s_data['reason'] = f"Статус: {status if status else 'Пусто'}"
                 not_paid_list.append(s_data)

    missing_in_students = []
    # Check payments that have an ID but that ID is not in students list
    for s_id, p_data in payments_with_id.items():
        if s_id not in all_students:
            # Only report if they actually paid or have a record for this month?
            # Or just report existence?
            # Let's report if they have a record.
            missing_in_students.append(p_data)
            
    for p_data in payments_without_id:
        missing_in_students.append(p_data)

    # Output Generation
    output = []
    output.append(f"Город: {city_name}")
    output.append(f"Месяц: {month}")
    output.append(f"Ученики: {len(all_students)}")
    # Count of those who PAID
    paid_count = len(all_students) - len(not_paid_list)
    output.append(f"Оплатили: {paid_count}")
    output.append(f"Не оплатили: {len(not_paid_list)}")
    output.append("")

    if not_paid_list:
        output.append("Список не оплативших:")
        for s in not_paid_list:
            output.append(f"{s['name']} ({s['phone']}) - {s.get('reason')} {s['url']}")
    else:
        output.append("Все ученики оплатили!")

    output.append("")
    
    if missing_in_students:
        output.append("Отсутствуют в базе учеников (но есть в оплатах):")
        for p in missing_in_students:
            output.append(f"{p['name']} ({p['phone']}) {p['url']}")
            
    return "\n".join(output)
