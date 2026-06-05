# Student Management Module

A custom and comprehensive education management module for Odoo 19 designed to manage student profiles, class allocation, subject enrollment, results processing, and automated fee billing.

---

## Features

### 1. Student Profile Management
* **Dual-Model Syncing**: Automatically inherits and syncs with `res.partner` and `res.users`.
* **Validation Guards**: Age validation (must be > 0), unique roll numbers, and regex-validated email addresses.
* **Status Tracking**: Student lifecycle states (`Draft`, `Active`, and `Inactive`).
* **Easy Registration**: Send automatic registration emails through Odoo mail templates.

### 2. Standards & Divisions
* **Class Allocation**: Define standards and divisions (e.g., `10-A`, `12-B`) with custom room numbers, capacity tracking, and standard fees.
* **Auto-Population**: Changing a student's standard auto-populates their course subjects based on the standard configuration.

### 3. Subject Configuration
* Manage available subjects per standard/class.
* Many-to-many relationship with students.

### 4. Grading & Results Processing
* **Overall Results**: Document overall percentage score and assign letter grades (`A`, `B`, `C`, `D`, `F`) automatically.
* **Subject Results**: Specify marks per subject. Built-in validation constraints prevent duplicate subject entries on a single result card.
* **Allowed Subjects Domain**: Dynamically filter subject options so teachers can only add results for subjects the student is registered for.

### 5. Automated Fees & Billing
* **Standard-Based Fee Auto-Creation**: Creating a student automatically generates a draft fee invoice matching their standard's base fee.
* **Odoo Sales & Invoices Integration**: Pay fees by generating a Quotation/Sales Order (`sale.order`) and an Invoice (`account.move`) automatically with a click.
* **Fees Wizard**: Easily create ad-hoc/custom fee bills for students.

### 6. Student Portal & Online Registration
* **Frontend Portal**: Dedicated customer portal page for students to view their details, subject results, and fee status.
* **Registration Page**: Dedicated registration page templates for online student admission.

### 7. Import / Export Scripts
* **Import Script**: Import student and user profiles from Excel files, automatically setting default classes and generating matching system credentials.
* **Export Script**: Export student profiles, logins, statuses, and fee records to Excel sheets.

---

## Directory Structure

```text
student_management/
├── controllers/          # Portal routing and online registration templates
│   └── portal.py         
├── data/                 # Email templates, data fixtures, and dummy Excel records
├── models/               # Core Odoo python models
│   ├── student.py        # student.management (inherits res.partner)
│   ├── student_standard.py  # student.standard
│   ├── student_subject.py   # student.subject
│   ├── student_result.py    # student.result & student.result.line
│   ├── student_fees.py      # student.fees (links to sale.order & account.move)
│   └── res_users.py      # User model modifications/hooks
├── scripts/              # Shell scripts for batch import/export via Odoo Shell
│   ├── import_students.py
│   └── export_students.py
├── security/             # Security groups (Admin, Teacher, Student) and ACL rules
├── views/                # XML UI Views (lists, forms, search, menus, portal/web pages)
└── wizard/               # Status modification and fee generation wizards
```

---

## Installation & Setup

1. Make sure Python dependency `openpyxl` is installed in your Odoo environment:
   ```bash
   pip install openpyxl
   ```
2. Add the `student_management` folder path to your Odoo `addons_path` in `odoo.conf`.
3. Restart the Odoo service.
4. Activate Developer Mode in Odoo, navigate to **Apps** -> **Update Apps List**, and search for "Student Management".
5. Click **Install**.

---

## Running Import & Export Scripts

These scripts are designed to be run through Odoo Shell.

### 1. Import Students
Loads the Excel spreadsheet located at `data/student_dummy_records.xlsx` and creates matching Student profiles and user logins (`password123`).
```bash
docker-compose exec odoo odoo shell -c /etc/odoo/odoo.conf < /mnt/production-addons/student_management/scripts/import_students.py
```

### 2. Export Students
Queries the Odoo database and exports all active students to `data/data.xlsx`.
```bash
docker-compose exec odoo odoo shell -c /etc/odoo/odoo.conf < /mnt/production-addons/student_management/scripts/export_students.py
```