/** @odoo-module **/

import { ProductCatalogKanbanRecord } from "@product/product_catalog/kanban_record";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { DuplicateProductDialog } from "./duplicate_product_dialog";

patch(ProductCatalogKanbanRecord.prototype, {
    setup() {
        super.setup();
        this.dialogService = useService("dialog");
        this.orm = useService("orm");
        this.initialQuantity = this.productCatalogData.quantity;
    },

    async updateQuantity(quantity) {
        if (this.productCatalogData.readOnly) {
            return;
        }

        // If the order is a sale.order and initialQuantity > 0
        if (this.env.orderResModel === "sale.order" && this.initialQuantity > 0) {
            const isIncrease = quantity > this.initialQuantity;
            const isDecrease = quantity < this.initialQuantity;

            if (isIncrease || isDecrease) {
                try {
                    // Fetch the lines info for this product
                    const lines = await this.orm.call(this.env.orderResModel, 'get_product_lines_info', [
                        this.env.orderId,
                        this.env.productId
                    ]);

                    // For INCREASE: always show popup if the item already exists (lines.length >= 1)
                    if (isIncrease && lines && lines.length >= 1) {
                        this.dialogService.add(DuplicateProductDialog, {
                            productName: this.props.record.data.display_name || this.props.record.data.name || 'Product',
                            qtyAdded: quantity - this.initialQuantity,
                            lines: lines,
                            onUpdateExisting: async (selectedLineId) => {
                                const price = await this.orm.call(this.env.orderResModel, 'apply_catalog_duplicate_choice_custom', [
                                    this.env.orderId,
                                    this.env.productId,
                                    parseInt(selectedLineId, 10),
                                    'update_existing',
                                    quantity,
                                    this.initialQuantity
                                ]);
                                this.productCatalogData.price = parseFloat(price);
                                // Update local states
                                this.productCatalogData.quantity = quantity;
                                this.initialQuantity = quantity;
                                this.render();
                            },
                            onAddAsNewLine: async () => {
                                const defaultLineId = lines[0].id;
                                const price = await this.orm.call(this.env.orderResModel, 'apply_catalog_duplicate_choice_custom', [
                                    this.env.orderId,
                                    this.env.productId,
                                    defaultLineId,
                                    'add_new',
                                    quantity,
                                    this.initialQuantity
                                ]);
                                this.productCatalogData.price = parseFloat(price);
                                // Update local states
                                this.productCatalogData.quantity = quantity;
                                this.initialQuantity = quantity;
                                this.render();
                            },
                            onCancel: () => {
                                // Revert input quantity
                                this.productCatalogData.quantity = this.initialQuantity;
                                this.render();
                            }
                        });
                        return;
                    } 
                    // For DECREASE: only show popup if multiple lines exist
                    else if (isDecrease && lines && lines.length > 1) {
                        this.dialogService.add(DuplicateProductDialog, {
                            productName: this.props.record.data.display_name || this.props.record.data.name || 'Product',
                            qtyAdded: this.initialQuantity - quantity,
                            lines: lines,
                            isDecrease: true,
                            title: "Decrease Product Quantity",
                            onUpdateExisting: async (selectedLineId) => {
                                const decreaseQty = this.initialQuantity - quantity;
                                const price = await this.orm.call(this.env.orderResModel, 'apply_catalog_decrease_choice_custom', [
                                    this.env.orderId,
                                    this.env.productId,
                                    parseInt(selectedLineId, 10),
                                    decreaseQty
                                ]);
                                this.productCatalogData.price = parseFloat(price);
                                this.productCatalogData.quantity = quantity;
                                this.initialQuantity = quantity;
                                this.render();
                            },
                            onCancel: () => {
                                // Revert input quantity
                                this.productCatalogData.quantity = this.initialQuantity;
                                this.render();
                            }
                        });
                        return;
                    }
                } catch (error) {
                    console.error("Error showing duplicate catalog warning:", error);
                }
            }
        }

        // Normal update (decrease/increase on single line, or not in quotation, or not sale.order)
        this.initialQuantity = quantity || 0;
        super.updateQuantity(quantity);
    }
});
