from odoo import models, fields, api
from odoo.exceptions import ValidationError
import re


class Student(models.Model):
    _name = 'student.management'
    _description = 'Student Management'
    _inherit = ['mail.thread']
    _inherits = {'res.partner': 'partner_id'}
    _sql_constraints = [
        (
            'unique_roll_number',
            'unique(roll_number)',
            'Roll Number must be unique.'
        )
    ]

    partner_id = fields.Many2one(
        'res.partner',
        string='Partner',
        required=True,
        ondelete='cascade'
    )
    roll_number = fields.Char(string='Roll Number', required=True)
    age = fields.Integer(string='Age')
    admission_date = fields.Date(string='Admission Date')
    standard_id = fields.Many2one(
        'student.standard',
        string='Standard'
    )
    standard = fields.Char(
        string='Standard Name',
        related='standard_id.standard',
        store=True,
        readonly=True
    )
    subject_ids = fields.Many2many(
        'student.subject',
        'student_subject_rel',
        'student_id',
        'subject_id',
        string="Subjects"
    )

    @api.onchange('standard_id')
    def _onchange_standard_id(self):
        if self.standard_id:
            # Auto-populate subjects with all subjects belonging to the selected standard
            subjects = self.env['student.subject'].search([('standard_name', '=', self.standard_id.standard)])
            self.subject_ids = [(6, 0, subjects.ids)]
        else:
            self.subject_ids = False
    result_ids = fields.One2many(
        'student.result',
        'student_id',
        string='Results'
    )
    fee_ids = fields.One2many(
        'student.fees',
        'student_id',
        string='Fees'
    )
    fee_status = fields.Selection([
        ('no_fees', 'No Fees'),
        ('unpaid', 'Unpaid'),
        ('paid', 'Paid'),
    ], string='Fee Status', compute='_compute_fee_status', store=True, tracking=True)
    quotation_count = fields.Integer(
        string='Quotations Count',
        compute='_compute_quotation_count'
    )

    @api.depends('fee_ids.state')
    def _compute_fee_status(self):
        for student in self:
            if not student.fee_ids:
                student.fee_status = 'no_fees'
            elif any(fee.state == 'draft' for fee in student.fee_ids):
                student.fee_status = 'unpaid'
            else:
                student.fee_status = 'paid'
    
    status = fields.Selection(
        [
            ('draft', 'Draft'),
            ('active', 'Active'),
            ('inactive', 'Inactive')
        ],
        string='Status',
        default='draft',
        tracking=True
    )
    
    @api.constrains('age')
    def _check_age(self):
        for record in self:
            if record.age and record.age <= 0:
                raise ValidationError("Age must be greater than zero.")
            
    @api.constrains('email')
    def _check_email(self):
        pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    
        for record in self:
            if record.email and not re.match(pattern, record.email):
                raise ValidationError("Please enter a valid email address.")
    @api.model_create_multi
    def create(self, vals_list):
        partner_model = self.env['res.partner']
        for vals in vals_list:
            if not vals.get('partner_id'):
                email = vals.get('email')
                existing_partner = False
                if email:
                    existing_partner = partner_model.sudo().search([('email', '=', email)], limit=1)
                if existing_partner:
                    vals['partner_id'] = existing_partner.id
                else:
                    partner_vals = {}
                    for field_name in list(vals.keys()):
                        if field_name in partner_model._fields:
                            partner_vals[field_name] = vals[field_name]
                    partner = partner_model.sudo().create(partner_vals)
                    vals['partner_id'] = partner.id
        
        records = super().create(vals_list)
        
        # Auto-create draft fees if the selected standard has a fees amount
        for record in records:
            if record.standard_id and record.standard_id.fees_amount > 0:
                self.env['student.fees'].create({
                    'student_id': record.id,
                    'description': f"School Fees for {record.standard_id.name}",
                    'amount': record.standard_id.fees_amount,
                })
        return records

    @api.model
    def _register_hook(self):
        super()._register_hook()
        students = self.sudo().search([])
        for student in students:
            if not student.email:
                continue
            user = self.env['res.users'].sudo().search([
                '|', ('login', '=', student.email), ('email', '=', student.email)
            ], limit=1)
            if user and user.partner_id != student.partner_id:
                old_partner = user.partner_id
                self.env.cr.execute("UPDATE res_users SET partner_id = %s WHERE id = %s", (student.partner_id.id, user.id))
                self.env.cr.execute("UPDATE res_partner SET active = False WHERE id = %s", (old_partner.id,))
                self.env.registry.clear_cache()


    def action_open_status_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Change Status',
            'res_model': 'student.status.wizard',
            'view_mode': 'form',
            'target': 'new',
             'context': {
                'default_student_id': self.id,
                'default_new_status': self.status,
            }
        }

    def action_open_fees_wizard(self):
        self.ensure_one()
        default_amount = self.standard_id.fees_amount or 0.0
        return {
            'type': 'ir.actions.act_window',
            'name': 'Create Fees',
            'res_model': 'student.fees.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_student_id': self.id,
                'default_amount': default_amount,
            }
        }

    def _compute_quotation_count(self):
        for record in self:
            record.quotation_count = self.env['sale.order'].sudo().search_count([
                ('partner_id', '=', record.partner_id.id)
            ])

    def action_view_quotations(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Quotations',
            'res_model': 'sale.order',
            'view_mode': 'list,form',
            'domain': [('partner_id', '=', self.partner_id.id)],
            'context': {'default_partner_id': self.partner_id.id},
        }