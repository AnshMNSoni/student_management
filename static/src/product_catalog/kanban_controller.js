/** @odoo-module **/

import { ProductCatalogKanbanController } from "@product/product_catalog/kanban_controller";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { DuplicateProductDialog } from "./duplicate_product_dialog";

patch(ProductCatalogKanbanController.prototype, {
    setup() {
        super.setup();
        this.dialogService = useService("dialog");
    },

    async backToQuotation() {
        if (this.orderResModel === "sale.order") {
            try {
                const duplicates = await this.orm.call(this.orderResModel, 'check_catalog_duplicates', [this.orderId]);
                if (duplicates && duplicates.length > 0) {
                    await this.processDuplicates(duplicates);
                    return;
                }
            } catch (error) {
                console.error("Error checking catalog duplicates:", error);
            }
        }
        await super.backToQuotation();
    },

    async processDuplicates(duplicates) {
        if (duplicates.length === 0) {
            // All duplicates processed, go back to quotation
            await super.backToQuotation();
            return;
        }

        const currentDuplicate = duplicates[0];
        const remainingDuplicates = duplicates.slice(1);

        this.dialogService.add(DuplicateProductDialog, {
            productName: currentDuplicate.product_name,
            qtyAdded: currentDuplicate.curr_qty - currentDuplicate.orig_qty,
            onUpdateExisting: async () => {
                await this.orm.call(this.orderResModel, 'apply_catalog_duplicate_choice', [
                    this.orderId,
                    currentDuplicate.product_id,
                    currentDuplicate.line_id,
                    'update_existing'
                ]);
                await this.processDuplicates(remainingDuplicates);
            },
            onAddAsNewLine: async () => {
                await this.orm.call(this.orderResModel, 'apply_catalog_duplicate_choice', [
                    this.orderId,
                    currentDuplicate.product_id,
                    currentDuplicate.line_id,
                    'add_new'
                ]);
                await this.processDuplicates(remainingDuplicates);
            },
            onCancel: async () => {
                await this.orm.call(this.orderResModel, 'apply_catalog_duplicate_choice', [
                    this.orderId,
                    currentDuplicate.product_id,
                    currentDuplicate.line_id,
                    'cancel'
                ]);
                await this.processDuplicates(remainingDuplicates);
            }
        });
    }
});
