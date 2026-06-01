from odoo import models, fields

class StudentSubject(models.Model):
    _name = 'student.subject'
    _description = 'Student Subject'

    name = fields.Char(string="Subject Name", required=True)
    standard_name = fields.Char(
        string="Standard"
    )
