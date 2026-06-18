from odoo import models, fields

class SaleOrderPackage(models.Model):
    _name = 'sale.order.package'
    _description = 'Sale Order Package'
    _order = 'name'

    name = fields.Char(string='Package Name', required=True)
    line_ids = fields.One2many('sale.order.package.line', 'package_id', string='Products')


class SaleOrderPackageLine(models.Model):
    _name = 'sale.order.package.line'
    _description = 'Sale Order Package Line'

    package_id = fields.Many2one('sale.order.package', string='Package', ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    quantity = fields.Float(string='Quantity', default=1.0, required=True)
