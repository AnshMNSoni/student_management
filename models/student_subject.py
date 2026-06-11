from odoo import models, fields

class StudentSubject(models.Model):
    _name = 'student.subject'
    _description = 'Student Subject'

    name = fields.Char(string="Subject Name", required=True)
    standard_name = fields.Char(
        string="Standard"
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company
    )
