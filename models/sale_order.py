from odoo import models, fields, api, Command

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    package_id = fields.Many2one('sale.order.package', string='Package')

    @api.onchange('package_id')
    def _onchange_package_id(self):
        if self.package_id:
            # Clear existing order lines and recreate them based on package lines
            lines = [Command.clear()]
            for line in self.package_id.line_ids:
                lines.append(Command.create({
                    'product_id': line.product_id.id,
                    'product_uom_qty': line.quantity,
                }))
            self.order_line = lines
        else:
            self.order_line = [Command.clear()]
