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
        ('inactive', 'Inactive'),
        ('active', 'Active')
    ], string="New Status", required=True)

    reason = fields.Text(string="Reason")

    def action_confirm(self):
        self.ensure_one()

        if self.student_id.status == self.new_status:
            raise ValidationError(
                "Student already has this status."
            )

        old_status = self.student_id.status
        self.student_id.write({
            'status': self.new_status
        })

        # Post custom status update in chatter
        body = f"Status changed: {old_status.capitalize()} to {self.new_status.capitalize()} - Date: {fields.Date.context_today(self)}"
        if self.reason:
            body += f" - Reason: {self.reason}"
        self.student_id.message_post(body=body, subtype_xmlid="mail.mt_note")

        return {'type': 'ir.actions.act_window_close'}