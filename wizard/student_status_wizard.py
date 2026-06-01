from odoo import models, fields
from odoo.exceptions import ValidationError


class StudentStatusWizard(models.TransientModel):
    _name = 'student.status.wizard'
    _description = 'Student Status Wizard'

    student_id = fields.Many2one(
        'student.management',
        string="Student",
        required=True
    )

    new_status = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('inactive', 'Inactive')
    ], string="New Status", required=True)

    reason = fields.Text(string="Reason")

    def action_confirm(self):
        self.ensure_one()

        if self.student_id.status == self.new_status:
            raise ValidationError(
                "Student already has this status."
            )

        self.student_id.write({
            'status': self.new_status
        })

        return {'type': 'ir.actions.act_window_close'}