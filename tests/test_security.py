from odoo.tests.common import TransactionCase
from odoo.exceptions import AccessError, ValidationError
from odoo import Command

class TestStudentSecurity(TransactionCase):

    def setUp(self):
        super(TestStudentSecurity, self).setUp()

        # Groups
        self.group_student = self.env.ref('student_management.group_student')
        self.group_teacher = self.env.ref('student_management.group_teacher')
        self.group_admin = self.env.ref('student_management.group_admin')

        # Create Standard
        self.standard = self.env['student.standard'].create({
            'standard': '10',
            'division': 'A',
        })

        # Create Student 1 (Charlie)
        self.student_charlie = self.env['student.management'].create({
            'name': 'Charlie',
            'roll_number': 'S108',
            'age': 15,
            'email': 'charlie.sec@example.com',
            'standard_id': self.standard.id,
        })
        self.user_charlie = self.env['res.users'].create({
            'name': 'Charlie Student',
            'login': 'charlie.sec@example.com',
            'email': 'charlie.sec@example.com',
            'partner_id': self.student_charlie.partner_id.id,
            'group_ids': [Command.set([self.group_student.id])]
        })

        # Create Student 2 (Lucy)
        self.student_lucy = self.env['student.management'].create({
            'name': 'Lucy',
            'roll_number': 'S109',
            'age': 15,
            'email': 'lucy.sec@example.com',
            'standard_id': self.standard.id,
        })
        self.user_lucy = self.env['res.users'].create({
            'name': 'Lucy Student',
            'login': 'lucy.sec@example.com',
            'email': 'lucy.sec@example.com',
            'partner_id': self.student_lucy.partner_id.id,
            'group_ids': [Command.set([self.group_student.id])]
        })

        # Create Teacher User
        self.user_teacher = self.env['res.users'].create({
            'name': 'Teacher John',
            'login': 'teacher.john@example.com',
            'email': 'teacher.john@example.com',
            'group_ids': [Command.set([self.group_teacher.id])]
        })

        # Create Admin User
        self.user_admin = self.env['res.users'].create({
            'name': 'Admin Jane',
            'login': 'admin.jane@example.com',
            'email': 'admin.jane@example.com',
            'group_ids': [Command.set([self.group_admin.id])]
        })

    def test_01_student_access_rights(self):
        """Test student group can only read their own student, result, fees records."""
        # 1. Reading student record
        # A student can search and read their own record
        charlie_student_model = self.env['student.management'].with_user(self.user_charlie)
        my_record = charlie_student_model.search([])
        self.assertEqual(my_record, self.student_charlie, "Student should only find their own student record.")

        # A student cannot read another student's record directly
        with self.assertRaises(AccessError):
            charlie_student_model.browse(self.student_lucy.id).read(['name'])

        # 2. Writing/Creating/Unlinking student record
        with self.assertRaises(AccessError):
            charlie_student_model.browse(self.student_charlie.id).write({'age': 16})

        with self.assertRaises(AccessError):
            charlie_student_model.create({
                'name': 'Hack Student',
                'roll_number': 'SHACK',
                'age': 15,
                'email': 'hack@example.com',
                'standard_id': self.standard.id,
            })

        with self.assertRaises(AccessError):
            charlie_student_model.browse(self.student_charlie.id).unlink()

    def test_02_teacher_access_rights(self):
        """Test teacher group has full read/write/create on students, but cannot delete students or manage standards."""
        teacher_student_model = self.env['student.management'].with_user(self.user_teacher)
        teacher_standard_model = self.env['student.standard'].with_user(self.user_teacher)

        # Teacher can search and read all students
        all_students = teacher_student_model.search([])
        self.assertIn(self.student_charlie, all_students)
        self.assertIn(self.student_lucy, all_students)

        # Teacher can create a student
        new_student = teacher_student_model.create({
            'name': 'New Student By Teacher',
            'roll_number': 'S110',
            'age': 14,
            'email': 'new.student.teacher@example.com',
            'standard_id': self.standard.id,
        })
        self.assertTrue(new_student.exists())

        # Teacher can modify student
        new_student.write({'age': 15})

        # Teacher CANNOT unlink student (access_teacher_student_management has perm_unlink = 0)
        with self.assertRaises(AccessError):
            new_student.unlink()

        # Teacher CANNOT create standard (access_teacher_student_standard has perm_create = 0)
        with self.assertRaises(AccessError):
            teacher_standard_model.create({
                'standard': '11',
                'division': 'A',
            })

    def test_03_admin_access_rights(self):
        """Test admin group has complete access permissions."""
        admin_student_model = self.env['student.management'].with_user(self.user_admin)
        admin_standard_model = self.env['student.standard'].with_user(self.user_admin)

        # Admin can create standard
        new_std = admin_standard_model.create({
            'standard': '11',
            'division': 'A',
        })
        self.assertTrue(new_std.exists())

        # Admin can create, modify, and unlink student
        student = admin_student_model.create({
            'name': 'Admin Student',
            'roll_number': 'S111',
            'age': 15,
            'email': 'admin.student@example.com',
            'standard_id': new_std.id,
        })
        student.write({'age': 16})
        student.unlink()
        self.assertFalse(student.exists())
