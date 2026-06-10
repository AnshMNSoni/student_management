# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError
from odoo import fields

class TestStudent(TransactionCase):

    def setUp(self):
        super(TestStudent, self).setUp()
        
        # Create standard for testing
        self.standard_10 = self.env['student.standard'].create({
            'standard': '10',
            'division': 'A',
            'fees_amount': 5000.0,
            'room_number': 'Room 101',
            'strength': 30
        })
        
        # Create subjects for standard 10
        self.subject_math = self.env['student.subject'].create({
            'name': 'Mathematics',
            'standard_name': '10'
        })
        self.subject_science = self.env['student.subject'].create({
            'name': 'Science',
            'standard_name': '10'
        })

    def test_01_student_creation_new_partner(self):
        """Test that creating a student automatically creates a new res.partner."""
        student = self.env['student.management'].create({
            'name': 'John Doe',
            'roll_number': 'S101',
            'age': 15,
            'email': 'john.doe@example.com',
            'admission_date': fields.Date.today(),
            'standard_id': self.standard_10.id,
        })
        
        # Check partner creation
        self.assertTrue(student.partner_id, "A partner record should be automatically created.")
        self.assertEqual(student.partner_id.name, 'John Doe')
        self.assertEqual(student.partner_id.email, 'john.doe@example.com')

    def test_02_student_creation_reuse_partner(self):
        """Test that creating a student with an existing partner email reuses that partner."""
        partner = self.env['res.partner'].create({
            'name': 'Existing Partner',
            'email': 'existing@example.com',
        })
        
        student = self.env['student.management'].create({
            'name': 'Student Reuse',
            'roll_number': 'S102',
            'age': 16,
            'email': 'existing@example.com',
            'admission_date': fields.Date.today(),
            'standard_id': self.standard_10.id,
        })
        
        self.assertEqual(student.partner_id.id, partner.id, "The existing partner should be reused.")

    def test_03_age_constraints(self):
        """Test age constraints on student.management."""
        # Age <= 0 should raise validation error
        with self.assertRaises(ValidationError):
            s = self.env['student.management'].create({
                'name': 'Invalid Age Student',
                'roll_number': 'S103',
                'age': 0,
                'email': 'invalid.age@example.com',
                'standard_id': self.standard_10.id,
            })
            s.flush_recordset()
            
        with self.assertRaises(ValidationError):
            s = self.env['student.management'].create({
                'name': 'Negative Age Student',
                'roll_number': 'S104',
                'age': -5,
                'email': 'neg.age@example.com',
                'standard_id': self.standard_10.id,
            })
            s.flush_recordset()

    def test_04_email_validation(self):
        """Test email address pattern validation."""
        with self.assertRaises(ValidationError):
            s = self.env['student.management'].create({
                'name': 'Invalid Email Student',
                'roll_number': 'S105',
                'age': 14,
                'email': 'not_an_email',
                'standard_id': self.standard_10.id,
            })
            s.flush_recordset()

    def test_05_standard_onchange(self):
        """Test standard_id onchange populates subject_ids."""
        student = self.env['student.management'].new({
            'standard_id': self.standard_10.id,
        })
        
        # Trigger onchange manually
        student._onchange_standard_id()
        
        # We expect math and science to be populated
        expected_subjects = self.subject_math | self.subject_science
        # Use _origin to resolve virtual recordsets
        self.assertEqual(student.subject_ids._origin, expected_subjects, "Subjects from standard 10 should be auto-populated.")

    def test_06_auto_fee_creation(self):
        """Test draft fee record is automatically created if standard has fees_amount."""
        student = self.env['student.management'].create({
            'name': 'Fee Student',
            'roll_number': 'S106',
            'age': 15,
            'email': 'fee.student@example.com',
            'admission_date': fields.Date.today(),
            'standard_id': self.standard_10.id,
        })
        
        # Check if student.fees was created
        fees = self.env['student.fees'].search([('student_id', '=', student.id)])
        self.assertEqual(len(fees), 1, "One fee record should be created automatically.")
        self.assertEqual(fees.amount, 5000.0)
        self.assertEqual(fees.description, "School Fees for 10-A")
        self.assertEqual(fees.state, 'draft')
        self.assertEqual(student.fee_status, 'unpaid')

    def test_07_fee_payment_deadline_and_cron(self):
        """Test calculation of fee payment deadline and daily cron checker."""
        from dateutil.relativedelta import relativedelta
        today = fields.Date.today()
        
        # 1. Verify automatic calculation of deadline
        admission_date = today - relativedelta(days=45)
        student_overdue = self.env['student.management'].create({
            'name': 'Overdue Student',
            'roll_number': 'S107',
            'age': 15,
            'email': 'overdue.student@example.com',
            'admission_date': admission_date,
            'standard_id': self.standard_10.id,
        })
        
        expected_deadline = admission_date + relativedelta(months=1)
        self.assertEqual(student_overdue.fee_payment_deadline, expected_deadline)
        self.assertFalse(student_overdue.deadline_miss_mail_sent)
        
        # 2. Verify cron sends email to overdue student without timely invoice
        self.env['student.management']._cron_check_payment_deadline()
        self.assertTrue(student_overdue.deadline_miss_mail_sent, "Student should be marked as deadline missed sent.")
        
        # 3. Verify student with a timely invoice is NOT emailed
        student_with_invoice = self.env['student.management'].create({
            'name': 'Paid Student',
            'roll_number': 'S108',
            'age': 15,
            'email': 'paid.student@example.com',
            'admission_date': admission_date,
            'standard_id': self.standard_10.id,
        })
        
        # Check that fee was auto-created
        fee = self.env['student.fees'].search([('student_id', '=', student_with_invoice.id)], limit=1)
        self.assertTrue(fee)
        
        # Create a mock invoice dated before the deadline
        invoice_date = admission_date + relativedelta(days=15)
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': student_with_invoice.partner_id.id,
            'invoice_date': invoice_date,
        })
        fee.invoice_id = invoice.id
        
        # Run cron checker again
        self.env['student.management']._cron_check_payment_deadline()
        self.assertFalse(student_with_invoice.deadline_miss_mail_sent, "Student with timely invoice should not be marked as deadline missed sent.")

