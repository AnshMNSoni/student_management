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

    def test_catalog_duplicates_interactive_choices(self):
        # 1. Test get_product_lines_info with single line
        lines_info = self.sale_order.get_product_lines_info(self.product.id)
        self.assertEqual(len(lines_info), 1)
        self.assertEqual(lines_info[0]['quantity'], 2.0)
        self.assertEqual(lines_info[0]['section_name'], "")

        # 2. Add sections and multiple lines
        section = self.env['sale.order.line'].create({
            'order_id': self.sale_order.id,
            'name': 'Test Section Sofa',
            'display_type': 'line_section',
        })
        line2 = self.env['sale.order.line'].create({
            'order_id': self.sale_order.id,
            'product_id': self.product.id,
            'product_uom_qty': 3.0,
            'sequence': section.sequence + 1,
        })
        lines_info = self.sale_order.get_product_lines_info(self.product.id)
        self.assertEqual(len(lines_info), 2)
        # Verify section name computation
        line2_info = next(x for x in lines_info if x['id'] == line2.id)
        self.assertEqual(line2_info['section_name'], "Test Section Sofa")

        # 3. Test apply_catalog_duplicate_choice_custom 'update_existing'
        # Current: line1=2.0, line2=3.0. User increases total catalog qty to 7.0 (added=2.0)
        # We choose to update line2 (ID = line2.id)
        self.sale_order.apply_catalog_duplicate_choice_custom(
            product_id=self.product.id,
            line_id=line2.id,
            choice='update_existing',
            new_qty=7.0,
            initial_qty=5.0
        )
        self.assertEqual(self.sale_order.order_line[0].product_uom_qty, 2.0) # line1 unchanged
        self.assertEqual(line2.product_uom_qty, 5.0) # line2 updated to 3.0 + 2.0

        # 4. Test apply_catalog_duplicate_choice_custom 'add_new'
        # Current total is 7.0. User increases total catalog qty to 10.0 (added=3.0)
        self.sale_order.apply_catalog_duplicate_choice_custom(
            product_id=self.product.id,
            line_id=line2.id,
            choice='add_new',
            new_qty=10.0,
            initial_qty=7.0
        )
        # Existing lines should be unchanged
        self.assertEqual(self.sale_order.order_line[0].product_uom_qty, 2.0)
        self.assertEqual(line2.product_uom_qty, 5.0)
        # There should be a third line with qty 3.0
        sol_lines = self.sale_order.order_line.filtered(lambda l: not l.display_type)
        self.assertEqual(len(sol_lines), 3)
        new_line = sol_lines[2]
        self.assertEqual(new_line.product_id.id, self.product.id)
        self.assertEqual(new_line.product_uom_qty, 3.0)

        # 5. Test apply_catalog_decrease_choice_custom
        # Current: line1=2.0, line2=5.0, new_line=3.0 (Total: 10.0)
        # Let's decrease quantity on line2 by 2.0 (resulting in 3.0)
        self.sale_order.apply_catalog_decrease_choice_custom(
            product_id=self.product.id,
            line_id=line2.id,
            decrease_qty=2.0
        )
        self.assertEqual(line2.product_uom_qty, 3.0)

        # Let's decrease line2 further by 4.0 (which is more than its current qty 3.0, unlinking it)
        self.sale_order.apply_catalog_decrease_choice_custom(
            product_id=self.product.id,
            line_id=line2.id,
            decrease_qty=4.0
        )
        self.assertFalse(line2.exists())

