from odoo import models, fields, api
from odoo.exceptions import ValidationError


class StudentResults(models.Model):
    _name = 'student.result'
    _description = 'Student Overall Result'
    _rec_name = 'sequence'
    _order = 'id desc'

    student_id = fields.Many2one(
        'student.management',
        string='Student',
        required=True,
        ondelete='cascade'
    )
    standard_id = fields.Many2one(
        'student.standard',
        string='Standard',
        related='student_id.standard_id',
        store=True,
        readonly=True
    )  
    standard = fields.Char(
        string='Standard Name',
        related='standard_id.standard',
        store=True,
        readonly=True
    )
    sequence = fields.Integer(string='Sequence', index=True, readonly=True, copy=False)
    
    result_date = fields.Date(string='Result Date', required=True, default=fields.Date.today)
    
    result_line_ids = fields.One2many(
        'student.result.line',
        'result_id',
        string='Subject Results'
    )
    
    overall_percentage = fields.Float(
        string='Overall Result (%)',
        compute='_compute_overall',
        store=True
    )
    overall_grade = fields.Selection([
        ('A', 'A'),
        ('B', 'B'),
        ('C', 'C'),
        ('D', 'D'),
        ('F', 'F')
    ], string='Overall Grade', compute='_compute_overall_grade', store=True)

    @api.depends('result_line_ids.marks')
    def _compute_overall(self):
        for rec in self:
            lines = rec.result_line_ids
            if not lines:
                rec.overall_percentage = 0.0
                continue
            rec.overall_percentage = sum(lines.mapped('marks')) / len(lines)

    @api.depends('overall_percentage')
    def _compute_overall_grade(self):
        for rec in self:
            percentage = rec.overall_percentage
            if percentage is False or percentage is None:
                rec.overall_grade = False
            elif percentage >= 90:
                rec.overall_grade = 'A'
            elif percentage >= 75:
                rec.overall_grade = 'B'
            elif percentage >= 60:
                rec.overall_grade = 'C'
            elif percentage >= 50:
                rec.overall_grade = 'D'
            else:
                rec.overall_grade = 'F'

    @api.model
    def create(self, vals):
        if isinstance(vals, list):
            last = self.search([], order='sequence desc', limit=1)
            seq = last.sequence or 0
            for v in vals:
                if not v.get('sequence'):
                    seq += 1
                    v['sequence'] = seq
            return super(StudentResults, self).create(vals)
        else:
            if not vals.get('sequence'):
                last = self.search([], order='sequence desc', limit=1)
                vals['sequence'] = (last.sequence or 0) + 1
            return super(StudentResults, self).create(vals)


class StudentResultLine(models.Model):
    _name = 'student.result.line'
    _description = 'Student Result Line'

    result_id = fields.Many2one(
        'student.result',
        string='Overall Result',
        required=True,
        ondelete='cascade'
    )
    student_id = fields.Many2one(
        'student.management',
        string='Student',
        related='result_id.student_id',
        store=True,
        readonly=True
    )
    subject_id = fields.Many2one(
        'student.subject',
        string='Subject',
        required=True
    )
    marks = fields.Float(string='Marks', required=True)
    grade = fields.Selection([
        ('A', 'A'),
        ('B', 'B'),
        ('C', 'C'),
        ('D', 'D'),
        ('F', 'F')
    ], string='Grade', compute='_compute_grade', store=True)

    allowed_subject_ids = fields.Many2many(
        'student.subject',
        compute='_compute_allowed_subject_ids',
        string='Allowed Subjects'
    )

    @api.depends('marks')
    def _compute_grade(self):
        for rec in self:
            if rec.marks is False or rec.marks is None:
                rec.grade = False
            elif rec.marks >= 90:
                rec.grade = 'A'
            elif rec.marks >= 75:
                rec.grade = 'B'
            elif rec.marks >= 60:
                rec.grade = 'C'
            elif rec.marks >= 50:
                rec.grade = 'D'
            else:
                rec.grade = 'F'

    @api.depends('result_id', 'result_id.student_id', 'result_id.student_id.standard_id', 'result_id.result_line_ids', 'result_id.result_line_ids.subject_id')
    def _compute_allowed_subject_ids(self):
        for rec in self:
            student = rec.result_id.student_id
            if not student or not student.standard_id or not student.standard_id.standard:
                rec.allowed_subject_ids = self.env['student.subject']
                continue
            
            # Find all subjects for this student's standard
            standard_subjects = self.env['student.subject'].search([
                ('standard_name', '=', student.standard_id.standard)
            ])
            
            # Subtract subjects from other lines of the parent result record
            other_lines = rec.result_id.result_line_ids - rec
            other_subjects = other_lines.mapped('subject_id')
            
            rec.allowed_subject_ids = standard_subjects - other_subjects

    @api.constrains('result_id', 'subject_id')
    def _check_unique_subject(self):
        for record in self:
            if record.result_id and record.subject_id:
                duplicate = self.search([
                    ('result_id', '=', record.result_id.id),
                    ('subject_id', '=', record.subject_id.id),
                    ('id', '!=', record.id)
                ])
                if duplicate:
                    raise ValidationError(
                        f"A result record already exists for subject '{record.subject_id.name}' for this student's result."
                    )
