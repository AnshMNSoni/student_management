import json
from odoo import models, fields, api, Command

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    package_id = fields.Many2one('sale.order.package', string='Package')
    catalog_snapshot = fields.Text(string='Catalog Snapshot')

    @api.onchange('package_id')
    def _onchange_package_id(self):
        if self.package_id:
            lines = []
            for line in self.package_id.line_ids:
                lines.append(Command.create({
                    'product_id': line.product_id.id,
                    'product_uom_qty': line.quantity,
                }))
            self.order_line = lines

    def action_add_from_catalog(self):
        snapshot_data = []
        for line in self.order_line:
            if not line.display_type and line.product_id:
                snapshot_data.append({
                    'line_id': line.id,
                    'product_id': line.product_id.id,
                    'quantity': line.product_uom_qty,
                    'section_id': line.get_parent_section_line().id if line.get_parent_section_line() else False,
                })
        self.catalog_snapshot = json.dumps(snapshot_data)
        return super().action_add_from_catalog()

    def check_catalog_duplicates(self):
        self.ensure_one()
        if not self.catalog_snapshot:
            return []
        try:
            snapshot = json.loads(self.catalog_snapshot)
        except Exception:
            return []

        duplicates = []
        for item in snapshot:
            line = self.env['sale.order.line'].browse(item['line_id'])
            if line.exists() and line.product_uom_qty > item['quantity']:
                duplicates.append({
                    'product_id': item['product_id'],
                    'product_name': line.product_id.display_name,
                    'orig_qty': item['quantity'],
                    'curr_qty': line.product_uom_qty,
                    'line_id': line.id,
                })
        return duplicates

    def apply_catalog_duplicate_choice(self, product_id, line_id, choice):
        self.ensure_one()
        if not self.catalog_snapshot:
            return
        try:
            snapshot = json.loads(self.catalog_snapshot)
        except Exception:
            return

        item = next((x for x in snapshot if x['line_id'] == line_id), None)
        if not item:
            return

        line = self.env['sale.order.line'].browse(line_id)
        if not line.exists():
            return

        orig_qty = item['quantity']
        curr_qty = line.product_uom_qty

        if choice == 'update_existing':
            # Do nothing, Odoo already updated the existing line to curr_qty
            pass
        elif choice == 'add_new':
            # Revert the existing line to its original quantity
            line.product_uom_qty = orig_qty
            # Create a new line for the difference
            added_qty = curr_qty - orig_qty
            if added_qty > 0:
                self.env['sale.order.line'].create({
                    'order_id': self.id,
                    'product_id': product_id,
                    'product_uom_qty': added_qty,
                    'sequence': line.sequence + 1,
                })
        elif choice == 'cancel':
            # Revert the existing line to its original quantity
            line.product_uom_qty = orig_qty

    def _update_order_line_info(self, product_id, quantity, **kwargs):
        self.ensure_one()
        section_id = kwargs.get('section_id', False)
        sol = self.order_line.filtered(
            lambda l: l.product_id.id == product_id
            and l.get_parent_section_line().id == section_id,
        )
        if len(sol) > 1:
            from odoo.http import request
            if request:
                try:
                    request.update_context(catalog_skip_tracking=True)
                except RuntimeError:
                    pass
            if quantity == 0:
                if self.state in ['draft', 'sent']:
                    price_unit = sol[0]._get_discounted_price()
                    sol.unlink()
                    return price_unit
                else:
                    sol.product_uom_qty = 0
            else:
                current_total = sum(sol.mapped('product_uom_qty'))
                if quantity != current_total:
                    diff = quantity - current_total
                    last_line = sol[-1]
                    new_qty = last_line.product_uom_qty + diff
                    if new_qty > 0:
                        last_line.product_uom_qty = new_qty
                    else:
                        target = quantity
                        for line in sol:
                            if target > 0:
                                if line == sol[-1]:
                                    line.product_uom_qty = target
                                    target = 0
                                else:
                                    if target < line.product_uom_qty:
                                        line.product_uom_qty = target
                                        target = 0
                                    else:
                                        target -= line.product_uom_qty
                            else:
                                if self.state in ['draft', 'sent']:
                                    line.unlink()
                                else:
                                    line.product_uom_qty = 0
            active_line = sol.filtered(lambda l: l.exists())
            if active_line:
                return active_line[-1]._get_discounted_price()
            return 0
        else:
            return super()._update_order_line_info(product_id, quantity, **kwargs)

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _get_product_catalog_lines_data(self, **kwargs):
        res = super()._get_product_catalog_lines_data(**kwargs)
        if len(self) > 1:
            res['readOnly'] = self.order_id._is_readonly()
        return res
