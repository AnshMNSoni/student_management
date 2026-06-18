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
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        related='student_id.company_id',
        store=True,
        readonly=True
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
    ], string='Status', compute='_compute_state', store=True, readonly=True)

    @api.depends('sale_order_id.state', 'invoice_id.payment_state')
    def _compute_state(self):
        for record in self:
            if (record.sale_order_id and record.sale_order_id.state in ['sale', 'done']) or \
               (record.invoice_id and record.invoice_id.payment_state in ['paid', 'in_payment']):
                record.state = 'paid'
            else:
                record.state = 'draft'

    @api.model
    def default_get(self, fields_list):
        res = super(StudentFees, self).default_get(fields_list)
        student_id = res.get('student_id') or self.env.context.get('default_student_id')
        if student_id:
            student = self.env['student.management'].browse(student_id)
            if 'amount' in fields_list and not res.get('amount'):
                res['amount'] = student.standard_id.fees_amount or 0.0
            if ('description' in fields_list and (not res.get('description') or res.get('description') == 'School Fees')) and student.standard_id:
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
        import pdb; pdb.set_trace()
        for record in self:
            if record.sale_order_id or record.state == 'paid':
                continue

            partner = record.student_id.partner_id
            if not partner:
                raise ValidationError("The selected student has no associated partner record.")

            company = record.company_id or self.env.company
            self_comp = self.with_company(company)

            # Find or create a service product for "School Fees"
            product = self_comp.env['product.product'].search([('name', '=', 'School Fees')], limit=1)
            if not product:
                product_vals = {
                    'name': 'School Fees',
                    'type': 'service',
                    'invoice_policy': 'order',
                }
                if 'is_published' in self_comp.env['product.product']._fields:
                    product_vals['is_published'] = True
                if 'publish_date' in self_comp.env['product.product']._fields:
                    product_vals['publish_date'] = fields.Datetime.now()
                product = self_comp.env['product.product'].create(product_vals)
            elif product.invoice_policy != 'order':
                product.write({'invoice_policy': 'order'})

            # 1. Create Quotation (sale.order)
            sale_order = self_comp.env['sale.order'].create({
                'partner_id': partner.id,
                'company_id': company.id,
                'order_line': [
                    (0, 0, {
                        'name': record.description or "School Fees",
                        'product_id': product.id,
                        'product_uom_qty': 1.0,
                        'price_unit': record.amount,
                    })
                ]
            })

            # 2. Link sale order
            record.write({
                'sale_order_id': sale_order.id,
            })

    def action_create_invoice(self):
        import pdb; pdb.set_trace()
        for record in self:
            if not record.sale_order_id:
                continue
            if record.invoice_id:
                continue

            company = record.company_id or self.env.company
            self_comp = self.with_company(company)

            # Ensure the Sales Order is confirmed
            if record.sale_order_id.state in ['draft', 'sent']:
                record.sale_order_id.action_confirm()

            # Create the invoice
            invoices = record.sale_order_id._create_invoices(final=True)
            if invoices:
                invoices.action_post()
                record.write({
                    'invoice_id': invoices[0].id
                })

                # Try to automatically register the payment and mark the invoice as paid
                try:
                    payment_register = self_comp.env['account.payment.register'].with_context(
                        active_model='account.move',
                        active_ids=invoices.ids
                    ).create({})
                    payment_register._create_payments()
                except Exception as e:
                    self_comp.env['ir.logging'].sudo().create({
                        'name': 'student_management.fees',
                        'type': 'server',
                        'dbname': self_comp.env.cr.dbname,
                        'level': 'WARNING',
                        'message': f"Could not auto-register payment for invoice {invoices[0].id}: {str(e)}",
                        'path': 'models/student_fees.py',
                        'func': 'action_create_invoice',
                        'line': '0'
                    })

