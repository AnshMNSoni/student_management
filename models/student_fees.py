from odoo import models, fields, api
from odoo.exceptions import ValidationError

class StudentFees(models.Model):
    _name = 'student.fees'
    _description = 'Student Fees'
    _order = 'id desc'

    student_id = fields.Many2one(
        'student.management',
        string='Student',
        required=True,
        ondelete='cascade'
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
        res = super(StudentFees, self).default_get(fields_list)
        student_id = res.get('student_id') or self.env.context.get('default_student_id')
        if student_id:
            student = self.env['student.management'].browse(student_id)
            if 'amount' in fields_list and not res.get('amount'):
                res['amount'] = student.standard_id.fees_amount or 0.0
            if 'description' in fields_list and (not res.get('description') or res.get('description') == 'School Fees'):
                if student.standard_id:
                    res['description'] = f"School Fees for {student.standard_id.name}"
        return res

    @api.onchange('student_id')
    def _onchange_student_id(self):
        if self.student_id:
            if not self.amount and self.student_id.standard_id:
                self.amount = self.student_id.standard_id.fees_amount or 0.0
            if (not self.description or self.description == 'School Fees') and self.student_id.standard_id:
                self.description = f"School Fees for {self.student_id.standard_id.name}"

    invoice_id = fields.Many2one(
        'account.move',
        string='Invoice',
        readonly=True
    )
    sale_order_id = fields.Many2one(
        'sale.order',
        string='Sales Order',
        readonly=True
    )

    @api.constrains('amount')
    def _check_amount(self):
        for record in self:
            if record.amount <= 0:
                raise ValidationError("Fee amount must be greater than zero.")

    def _compute_display_name(self):
        for record in self:
            record.display_name = f"Fee #{record.id}" if record.id else "New"

    def action_pay(self):
        for record in self:
            if record.state == 'paid':
                continue

            partner = record.student_id.partner_id
            if not partner:
                raise ValidationError("The selected student has no associated partner record.")

            # Find or create a service product for "School Fees"
            product = self.env['product.product'].search([('name', '=', 'School Fees')], limit=1)
            if not product:
                product = self.env['product.product'].create({
                    'name': 'School Fees',
                    'type': 'service',
                })

            # 1. Create Quotation (sale.order)
            sale_order = self.env['sale.order'].create({
                'partner_id': partner.id,
                'order_line': [
                    (0, 0, {
                        'name': record.description or "School Fees",
                        'product_id': product.id,
                        'product_uom_qty': 1.0,
                        'price_unit': record.amount,
                    })
                ]
            })

            # 2. Link sale order and mark fees as paid
            record.write({
                'sale_order_id': sale_order.id,
                'state': 'paid'
            })
