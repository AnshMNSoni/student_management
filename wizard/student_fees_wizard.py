from odoo import models, fields, api

class StudentFeesWizard(models.TransientModel):
    _name = 'student.fees.wizard'
    _description = 'Student Fees Payment Wizard'

    student_id = fields.Many2one(
        'student.management',
        string='Student',
        required=True
    )
    description = fields.Char(
        string='Description',
        required=True,
        default='School Fees'
    )
    amount = fields.Float(
        string='Amount',
        required=True
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('paid', 'Paid'),
    ], string='Status', default='draft', readonly=True)

    @api.model
    def default_get(self, fields_list):
        res = super(StudentFeesWizard, self).default_get(fields_list)
        student_id = res.get('student_id') or self.env.context.get('default_student_id')
        if student_id:
            student = self.env['student.management'].browse(student_id)
            if 'amount' in fields_list and not res.get('amount'):
                res['amount'] = student.standard_id.fees_amount or 0.0
        return res

    def action_pay_fees(self):
        self.ensure_one()
        # Create student.fees record
        fee = self.env['student.fees'].create({
            'student_id': self.student_id.id,
            'description': self.description,
            'amount': self.amount,
        })
        # Pay fees (creates quotation, sale order, invoice, payment)
        fee.action_pay()

        # Update wizard state (mostly for UI consistency)
        self.write({'state': 'paid'})

        # Reload the student page to reflect new status and records
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
