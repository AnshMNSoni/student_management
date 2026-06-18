from odoo import models, fields, api
from odoo.exceptions import ValidationError

class SaleOrderPackage(models.Model):
    _name = 'sale.order.package'
    _description = 'Sale Order Package'
    _order = 'name'

    name = fields.Char(string='Package Name', required=True)
    line_ids = fields.One2many('sale.order.package.line', 'package_id', string='Products')
    selected_product_ids = fields.Many2many(
        'product.product', 
        string='Selected Products', 
        compute='_compute_selected_product_ids'
    )

    @api.depends('line_ids.product_id')
    def _compute_selected_product_ids(self):
        for record in self:
            record.selected_product_ids = record.line_ids.mapped('product_id')

    @api.constrains('line_ids')
    def _check_duplicate_products(self):
        for record in self:
            product_ids = record.line_ids.mapped('product_id.id')
            if len(product_ids) != len(set(product_ids)):
                raise ValidationError("You cannot add the same product multiple times in a package.")


class SaleOrderPackageLine(models.Model):
    _name = 'sale.order.package.line'
    _description = 'Sale Order Package Line'

    package_id = fields.Many2one('sale.order.package', string='Package', ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    quantity = fields.Float(string='Quantity', default=1.0, required=True)
