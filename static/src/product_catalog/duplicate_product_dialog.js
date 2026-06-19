/** @odoo-module **/

import { Dialog } from "@web/core/dialog/dialog";
import { Component } from "@odoo/owl";
import { useChildRef } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

export class DuplicateProductDialog extends Component {
    static template = "student_management.DuplicateProductDialog";
    static components = { Dialog };
    static props = {
        close: Function,
        productName: String,
        qtyAdded: Number,
        onUpdateExisting: Function,
        onAddAsNewLine: Function,
        onCancel: Function,
        title: { type: String, optional: true },
    };
    static defaultProps = {
        title: _t("Duplicate Product Found"),
    };

    setup() {
        this.modalRef = useChildRef();
        this.env.dialogData.dismiss = () => this._cancel();
    }

    async _updateExisting() {
        if (this.props.onUpdateExisting) {
            await this.props.onUpdateExisting();
        }
        this.props.close();
    }

    async _addAsNewLine() {
        if (this.props.onAddAsNewLine) {
            await this.props.onAddAsNewLine();
        }
        this.props.close();
    }

    async _cancel() {
        if (this.props.onCancel) {
            await this.props.onCancel();
        }
        this.props.close();
    }
}
