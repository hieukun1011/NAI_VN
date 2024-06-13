/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";
import { useInputField } from "@web/views/fields/input_field_hook";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

import { Component } from "@odoo/owl";

export class EmailFieldTree extends Component {
    setup() {
        if (this.props.value){
            this.props.value_data = this.props.value.substr(0, 3) + '******' + this.props.value.substr(-4);
        };
        useInputField({ getValue: () => this.props.value || "" });
    }
}

EmailFieldTree.template = "history_contact.EmailFieldTree";
EmailFieldTree.props = {
    ...standardFieldProps,
    placeholder: { type: String, optional: true },
};
EmailFieldTree.extractProps = ({ attrs }) => {
    return {
        placeholder: attrs.placeholder,
    };
};

EmailFieldTree.displayName = _lt("Email");
EmailFieldTree.supportedTypes = ["char"];


registry.category("fields").add("email_tree", EmailFieldTree);
