from odoo import models, fields, api
from odoo.exceptions import ValidationError

class StudentStandard(models.Model):
    _name = 'student.standard'
    _description = 'Student Standard'

    standard = fields.Char(string="Standard", required=True)
    division = fields.Char(string="Division/Grade", required=True, default="A")
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )
    name = fields.Char(
        string="Standard Name",
        compute="_compute_name",
        store=True,
        readonly=False
    )
    fees_amount = fields.Float(string="Fees Amount", default=0.0)
    room_number = fields.Char(string="Room Number")
    strength = fields.Integer(string="Strength")

    student_ids = fields.One2many(
        'student.management',
        'standard_id',
        string="Students"
    )

    subject_ids = fields.Many2many(
        'student.subject',
        compute='_compute_subject_ids',
        inverse='_inverse_subject_ids',
        string="Subjects"
    )

    @api.depends('standard', 'division')
    def _compute_name(self):
        for record in self:
            if record.standard and record.division:
                record.name = f"{record.standard}-{record.division}"
            elif record.standard:
                record.name = record.standard
            elif record.name:
                pass
            else:
                record.name = "New Standard"

    def _compute_subject_ids(self):
        for record in self:
            if record.standard:
                record.subject_ids = self.env['student.subject'].search([
                    ('standard_name', '=', record.standard)
                ])
            else:
                record.subject_ids = self.env['student.subject'].browse()

    def _inverse_subject_ids(self):
        for record in self:
            if not record.standard:
                continue
            db_subjects = self.env['student.subject'].search([('standard_name', '=', record.standard)])
            current_subjects = record.subject_ids
            for subject in current_subjects:
                if subject.standard_name != record.standard:
                    subject.standard_name = record.standard
            removed_subjects = db_subjects - current_subjects
            if removed_subjects:
                removed_subjects.unlink()

    @api.constrains('standard')
    def _check_standard_value(self):
        for record in self:
            if record.standard:
                val = record.standard.strip().upper()
                if len(val) == 1 and val.isalpha():
                    raise ValidationError(
                        "Please enter a valid Standard (e.g., 10, 12, XI) instead of a division letter."
                    )
                if val in ['A', 'B', 'C', 'D', 'E', 'F']:
                    raise ValidationError("Standard cannot be a division letter.")
