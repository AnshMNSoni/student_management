from odoo.tests.common import TransactionCase
from odoo import Command
import json

class TestSaleOrderCatalog(TransactionCase):

    def setUp(self):
        super(TestSaleOrderCatalog, self).setUp()
        self.partner = self.env['res.partner'].create({'name': 'Test Partner'})
        self.product = self.env['product.product'].create({
            'name': 'Test Product Sofa',
            'type': 'consu',
            'sale_ok': True,
        })
        self.sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [
                Command.create({
                    'product_id': self.product.id,
                    'product_uom_qty': 2.0,
                })
            ]
        })

    def test_catalog_snapshot_and_choices(self):
        # 1. Test Snapshot Action
        self.sale_order.action_add_from_catalog()
        self.assertTrue(self.sale_order.catalog_snapshot)
        snapshot = json.loads(self.sale_order.catalog_snapshot)
        self.assertEqual(len(snapshot), 1)
        self.assertEqual(snapshot[0]['product_id'], self.product.id)
        self.assertEqual(snapshot[0]['quantity'], 2.0)

        # Get line
        line = self.sale_order.order_line[0]

        # 2. Test check_catalog_duplicates with no change
        duplicates = self.sale_order.check_catalog_duplicates()
        self.assertEqual(len(duplicates), 0)

        # Update qty to 5 (simulating a catalog increase)
        line.product_uom_qty = 5.0
        duplicates = self.sale_order.check_catalog_duplicates()
        self.assertEqual(len(duplicates), 1)
        self.assertEqual(duplicates[0]['product_id'], self.product.id)
        self.assertEqual(duplicates[0]['orig_qty'], 2.0)
        self.assertEqual(duplicates[0]['curr_qty'], 5.0)

        # 3. Test choice: 'update_existing'
        self.sale_order.apply_catalog_duplicate_choice(self.product.id, line.id, 'update_existing')
        self.assertEqual(line.product_uom_qty, 5.0)
        self.assertEqual(len(self.sale_order.order_line), 1)

        # 4. Test choice: 'add_new'
        # Re-initialize to simulating change: line starts at 2, user changes to 5
        line.product_uom_qty = 5.0
        self.sale_order.apply_catalog_duplicate_choice(self.product.id, line.id, 'add_new')
        # Existing line must be reverted to 2
        self.assertEqual(line.product_uom_qty, 2.0)
        # There should be a new line with quantity 3 (5 - 2)
        self.assertEqual(len(self.sale_order.order_line), 2)
        new_line = self.sale_order.order_line[1]
        self.assertEqual(new_line.product_id.id, self.product.id)
        self.assertEqual(new_line.product_uom_qty, 3.0)

        # 5. Test choice: 'cancel'
        # Reset new line, make existing line 5 again
        new_line.unlink()
        line.product_uom_qty = 5.0
        self.sale_order.apply_catalog_duplicate_choice(self.product.id, line.id, 'cancel')
        # Existing line must be reverted to 2, no extra line
        self.assertEqual(line.product_uom_qty, 2.0)
        self.assertEqual(len(self.sale_order.order_line), 1)

    def test_multi_line_catalog_editing(self):
        line1 = self.sale_order.order_line[0]
        line2 = self.env['sale.order.line'].create({
            'order_id': self.sale_order.id,
            'product_id': self.product.id,
            'product_uom_qty': 3.0,
        })
        self.assertEqual(len(self.sale_order.order_line), 2)

        lines_info = self.sale_order._get_product_catalog_order_line_info([self.product.id])
        product_data = lines_info.get(self.product.id)
        self.assertIsNotNone(product_data)
        self.assertFalse(product_data.get('readOnly'))
        self.assertEqual(product_data.get('quantity'), 5.0)

        self.sale_order._update_order_line_info(self.product.id, 7.0)
        self.assertEqual(line1.product_uom_qty, 2.0)
        self.assertEqual(line2.product_uom_qty, 5.0)

        self.sale_order._update_order_line_info(self.product.id, 4.0)
        self.assertEqual(line1.product_uom_qty, 2.0)
        self.assertEqual(line2.product_uom_qty, 2.0)

        self.sale_order._update_order_line_info(self.product.id, 1.0)
        self.assertEqual(line1.product_uom_qty, 1.0)
        self.assertFalse(line2.exists())
