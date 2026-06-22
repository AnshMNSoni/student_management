/** @odoo-module **/

import { Dialog } from "@web/core/dialog/dialog";
import { Component, useState } from "@odoo/owl";
import { useChildRef } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

export class DuplicateProductDialog extends Component {
    static template = "student_management.DuplicateProductDialog";
    static components = { Dialog };
    static props = {
        close: Function,
        productName: String,
        qtyAdded: Number,
        lines: Array,
        isDecrease: { type: Boolean, optional: true },
        onUpdateExisting: Function,
        onAddAsNewLine: { type: Function, optional: true },
        onCancel: Function,
        title: { type: String, optional: true },
    };
    static defaultProps = {
        title: _t("Duplicate Product Found"),
    };

    setup() {
        this.modalRef = useChildRef();
        this.env.dialogData.dismiss = () => this._cancel();
        this.state = useState({
            selectedLineId: this.props.lines && this.props.lines.length > 0 ? this.props.lines[0].id : null,
            showLinePicker: this.props.isDecrease || false,
        });
    }

    async _updateExisting() {
        if (this.props.lines && this.props.lines.length > 1 && !this.state.showLinePicker) {
            this.state.showLinePicker = true;
            return;
        }
        if (this.props.onUpdateExisting) {
            await this.props.onUpdateExisting(this.state.selectedLineId);
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

    _goBack() {
        if (this.props.isDecrease) {
            this._cancel();
        } else {
            this.state.showLinePicker = false;
        }
    }
}
