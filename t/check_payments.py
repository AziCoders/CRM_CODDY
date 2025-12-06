import json
import os
import sys
import io

# Force UTF-8 output for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def check_payments(city_name="Nazran"):
    # Define paths
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(base_dir, "data", city_name)
    students_path = os.path.join(data_dir, "students.json")
    payments_path = os.path.join(data_dir, "payments.json")

    # Load data
    try:
        with open(students_path, 'r', encoding='utf-8') as f:
            students_data = json.load(f)
        with open(payments_path, 'r', encoding='utf-8') as f:
            payments_data = json.load(f)
    except FileNotFoundError as e:
        print(f"Error: File not found - {e}")
        return

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
    all_payments = {}
    for payment in payments_data.get("payments", []):
        s_id = payment.get("student_id")
        
        p_id = payment.get("ID")
        payment_record = {
            "name": payment.get("ФИО", "Unknown"),
            "url": payment.get("payment_url", ""),
            "student_id": s_id,
            "phone": payment.get("Phone", "")
        }
        
        if s_id:
            all_payments[s_id] = payment_record
        else:
            pass
            
    # Re-iterate to capture all payments for the "total" count and "missing in students" check
    payments_with_id = {}
    payments_without_id = []
    
    for payment in payments_data.get("payments", []):
        s_id = payment.get("student_id")
        p_record = {
             "name": payment.get("ФИО", "Unknown"),
             "url": payment.get("payment_url", ""),
             "phone": payment.get("Phone", "")
        }
        if s_id:
            payments_with_id[s_id] = p_record
        else:
            payments_without_id.append(p_record)

    # Comparison
    missing_in_payments = []
    for s_id, s_data in all_students.items():
        if s_id not in payments_with_id:
            missing_in_payments.append(s_data)

    missing_in_students = []
    # Check payments that have an ID but that ID is not in students list
    for s_id, p_data in payments_with_id.items():
        if s_id not in all_students:
            missing_in_students.append(p_data)
            
    for p_data in payments_without_id:
        missing_in_students.append(p_data)

    # Output
    print(f"{city_name}")
    print(f"Ученики: {len(all_students)} Оплата: {len(payments_data.get('payments', []))}")
    print("")

    for s in missing_in_payments:
        print(f"{s['name']} отсутствует в оплатах {s['phone']} {s['url']}")
    
    print("")
    
    for p in missing_in_students:
        print(f"{p['name']} отсутствует в учениках {p['phone']} {p['url']}")

if __name__ == "__main__":
    check_payments("Sunja")

