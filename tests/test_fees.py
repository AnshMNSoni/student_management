from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError
from odoo import fields

class TestStudentFees(TransactionCase):

    def setUp(self):
        super(TestStudentFees, self).setUp()
        
        # Setup standard and student
        self.standard = self.env['student.standard'].create({
            'standard': '12',
            'division': 'A',
            'fees_amount': 6000.0,
        })
        self.student = self.env['student.management'].create({
            'name': 'Bob Smith',
            'roll_number': 'S120',
            'age': 17,
            'email': 'bob.smith@example.com',
            'standard_id': self.standard.id,
        })
        # Remove automatically created fees if any (since setUp does auto fee creation)
        self.student.fee_ids.unlink()

    def test_01_fees_constraints(self):
        """Test validation on fee amount."""
        with self.assertRaises(ValidationError):
            self.env['student.fees'].create({
                'student_id': self.student.id,
                'description': 'Test negative fees',
                'amount': -100.0,
            })
        with self.assertRaises(ValidationError):
            self.env['student.fees'].create({
                'student_id': self.student.id,
                'description': 'Test zero fees',
                'amount': 0.0,
            })

    def test_02_fee_action_pay(self):
        """Test action_pay creates a sales order and updates fee state accordingly."""
        fee = self.env['student.fees'].create({
            'student_id': self.student.id,
            'description': 'Term 1 Fees',
            'amount': 3000.0,
        })

        # Pre-checks
        self.assertEqual(fee.state, 'draft')
        self.assertFalse(fee.sale_order_id)

        # Pay fee
        fee.action_pay()

        # Check sales order creation
        self.assertTrue(fee.sale_order_id, "Sales Order should be generated.")
        self.assertEqual(fee.sale_order_id.partner_id.id, self.student.partner_id.id)
        self.assertEqual(len(fee.sale_order_id.order_line), 1)
        self.assertEqual(fee.sale_order_id.order_line[0].price_unit, 3000.0)
        self.assertEqual(fee.sale_order_id.order_line[0].name, 'Term 1 Fees')
        
        # Confirm sales order to test state computation
        fee.sale_order_id.action_confirm()
        self.assertEqual(fee.state, 'paid', "Fee state should transition to paid after Sales Order confirmation.")
        # Re-compute status of student
        self.student._compute_fee_status()
        self.assertEqual(self.student.fee_status, 'paid', "Student fee status should transition to paid.")

    def test_03_fees_wizard(self):
        """Test the student fees wizard workflow."""
        # Open fees wizard with default values
        wizard_context = {
            'default_student_id': self.student.id,
        }
        
        # Check default amount
        default_vals = self.env['student.fees.wizard'].with_context(wizard_context).default_get(['amount'])
        self.assertEqual(default_vals.get('amount'), 6000.0, "Default amount in wizard should match standard fees.")

        # Create wizard record
        wizard = self.env['student.fees.wizard'].with_context(wizard_context).create({
            'student_id': self.student.id,
            'description': 'Wizard Paid Fees',
            'amount': 5500.0,
        })

        self.assertEqual(wizard.state, 'draft')

        # Trigger wizard payment action
        wizard.action_pay_fees()

        # Check wizard updates state to paid
        self.assertEqual(wizard.state, 'paid')

        # Check corresponding student.fees record
        fee = self.env['student.fees'].search([('student_id', '=', self.student.id)])
        self.assertEqual(len(fee), 1)
        self.assertEqual(fee.amount, 5500.0)
        self.assertEqual(fee.description, 'Wizard Paid Fees')
        self.assertTrue(fee.sale_order_id)
        
        # Check chatter log on student
        messages = self.env['mail.message'].search([
            ('model', '=', 'student.management'),
            ('res_id', '=', self.student.id),
        ])
        body_texts = [m.body for m in messages]
        has_message = any("Wizard Paid Fees" in body and "5500" in body for body in body_texts)
        self.assertTrue(has_message, "A chatter message should be logged for paid fees.")
