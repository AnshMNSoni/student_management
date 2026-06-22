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
        await super.backToQuotation();
    }
});
