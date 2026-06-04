import os
import openpyxl

def export_students(env):
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        excel_path = os.path.abspath(os.path.join(script_dir, '..', 'data', 'data.xlsx'))
    except NameError:
        excel_path = os.path.abspath(os.path.join(os.getcwd(), 'custom_addons', 'student_management', 'data', 'data.xlsx'))

    os.makedirs(os.path.dirname(excel_path), exist_ok=True)

    print("Locating student group and users...")
    group_student = env.ref('student_management.group_student', raise_if_not_found=False)
    if not group_student:
        print("Error: Student group (student_management.group_student) not found.")
        return

    users = group_student.user_ids
    if not users:
        print("No users found in the Student group.")
        return

    print(f"Found {len(users)} users in the Student group. Starting export...")

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Students"

    headers = ['Name', 'Login/Email', 'Roll Number', 'Age', 'Admission Date', 'Status', 'Fee Status']
    ws.append(headers)

    status_mapping = {
        'draft': 'Draft',
        'active': 'Active',
        'inactive': 'Inactive'
    }
    fee_status_mapping = {
        'no_fees': 'No Fees',
        'unpaid': 'Unpaid',
        'paid': 'Paid'
    }

    student_model = env['student.management']
    export_count = 0

    for user in users:
        student = student_model.search([('partner_id', '=', user.partner_id.id)], limit=1)

        name = user.name or ""
        login = user.login or ""
        
        if student:
            roll_number = student.roll_number or ""
            age = student.age or ""
            admission_date = student.admission_date.strftime('%Y-%m-%d') if student.admission_date else ""
            status = status_mapping.get(student.status, "")
            fee_status = fee_status_mapping.get(student.fee_status, "")
        else:
            roll_number = ""
            age = ""
            admission_date = ""
            status = ""
            fee_status = ""

        ws.append([name, login, roll_number, age, admission_date, status, fee_status])
        export_count += 1

    try:
        wb.save(excel_path)
        print(f"\nExport Finished: {export_count} records exported successfully to {excel_path}.")
    except Exception as e:
        print(f"Error saving workbook: {e}")

if 'env' in globals():
    export_students(env)
else:
    print("This script must be run inside Odoo Shell.")
    print("Usage: python odoo-bin shell -c odoo.conf < path/to/export_students.py")
