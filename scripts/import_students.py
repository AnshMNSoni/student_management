import os
import openpyxl
from datetime import datetime
from odoo import SUPERUSER_ID

def import_students(env):
    # Locate the Excel file relative to the script directory, with fallback for stdin pipes
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        excel_path = os.path.abspath(os.path.join(script_dir, '..', 'data', 'student_dummy_records.xlsx'))
    except NameError:
        excel_path = os.path.abspath(os.path.join(os.getcwd(), 'custom_addons', 'student_management', 'data', 'student_dummy_records.xlsx'))
    
    if not os.path.exists(excel_path):
        print(f"Excel file not found at: {excel_path}")
        return

    print("Mocking email sending systems to speed up import...")
    # Monkey-patch to prevent actual SMTP/mail operations during import
    mail_mail_class = type(env['mail.mail'])
    original_mail_send = mail_mail_class.send
    mail_mail_class.send = lambda *args, **kwargs: True

    res_users_class = type(env['res.users'])
    original_signup_email = getattr(res_users_class, '_send_signup_email', None)
    if original_signup_email:
        res_users_class._send_signup_email = lambda *args, **kwargs: True

    try:
        print(f"Loading workbook from {excel_path}...")
        wb = openpyxl.load_workbook(excel_path)
        sheet = wb.active

        # Find or create a default standard if one doesn't exist
        standard_model = env['student.standard']
        default_standard = standard_model.search([], limit=1)
        if not default_standard:
            print("No student standard found. Creating a default standard '10-A'...")
            default_standard = standard_model.create({
                'standard': '10',
                'division': 'A',
                'fees_amount': 500.0,
            })
            env.cr.commit()

        student_model = env['student.management']
        user_model = env['res.users']
        
        # Try to resolve the student group
        group_student = env.ref('student_management.group_student', raise_if_not_found=False)
        if not group_student:
            print("Warning: student_management.group_student not found. Users will be created without this group.")

        success_count = 0
        skipped_count = 0

        # Read rows (skip header)
        for row_idx, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
            name, roll_number, age, email, admission_date, status, fee_status = row

            if not name or not roll_number or not email:
                print(f"Row {row_idx}: Missing required fields (Name, Roll Number, or Email). Skipping.")
                skipped_count += 1
                continue

            # Clean strings
            name = str(name).strip()
            roll_number = str(roll_number).strip()
            email = str(email).strip()

            # Check if roll number already exists
            existing_student = student_model.search([('roll_number', '=', roll_number)], limit=1)
            if existing_student:
                # Silently skip to keep console clean, or log periodically
                skipped_count += 1
                continue

            # Check if email is already in use by a user
            existing_user = user_model.search([('login', '=', email)], limit=1)
            if existing_user:
                skipped_count += 1
                continue

            # Parse admission date
            if isinstance(admission_date, str):
                try:
                    admission_date = datetime.strptime(admission_date.strip(), '%Y-%m-%d').date()
                except ValueError:
                    admission_date = datetime.today().date()
            elif not admission_date:
                admission_date = datetime.today().date()

            # Parse status (selection field values: 'draft', 'active', 'inactive')
            status_val = 'draft'
            if status:
                status_lower = str(status).strip().lower()
                if status_lower in ['draft', 'active', 'inactive']:
                    status_val = status_lower

            # Parse fee status (selection field values: 'no_fees', 'unpaid', 'paid')
            fee_status_val = 'no_fees'
            if fee_status:
                fee_status_lower = str(fee_status).strip().lower()
                if fee_status_lower in ['no fees', 'no_fees']:
                    fee_status_val = 'no_fees'
                elif fee_status_lower == 'unpaid':
                    fee_status_val = 'unpaid'
                elif fee_status_lower == 'paid':
                    fee_status_val = 'paid'

            try:
                # 1. Create student record
                student = student_model.create({
                    'name': name,
                    'roll_number': roll_number,
                    'age': int(age) if age else 0,
                    'email': email,
                    'standard_id': default_standard.id,
                    'admission_date': admission_date,
                    'status': status_val,
                    'fee_status': fee_status_val,
                })

                # 2. Create user record and associate with student's partner
                user_vals = {
                    'name': name,
                    'login': email,
                    'email': email,
                    'partner_id': student.partner_id.id,
                    'password': 'password123',
                }
                if group_student:
                    user_vals['group_ids'] = [(6, 0, [group_student.id])]
                    
                user_model.create(user_vals)
                success_count += 1

                # Commit batch every 50 records
                if success_count % 50 == 0:
                    env.cr.commit()
                    print(f"Imported {success_count} students...")

            except Exception as e:
                print(f"Row {row_idx}: Failed to import due to: {e}. Skipping.")
                skipped_count += 1

        # Commit final transaction to database
        env.cr.commit()
        print(f"\nImport Finished: {success_count} new students imported successfully, {skipped_count} skipped/existing.")

    finally:
        # Restore original email/SMTP functions
        print("Restoring email sending functions...")
        mail_mail_class.send = original_mail_send
        if original_signup_email:
            res_users_class._send_signup_email = original_signup_email

# Execute when run within Odoo Shell
if 'env' in globals():
    import_students(env)
else:
    print("This script must be run inside Odoo Shell.")
    print("Usage: python odoo-bin shell -c odoo.conf < path/to/import_students.py")
