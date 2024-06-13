/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";
import { useInputField } from "@web/views/fields/input_field_hook";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

import { Component } from "@odoo/owl";

export class PhoneFieldTree extends Component {
    setup() {
        if (this.props.value){
            this.props.value_data = this.props.value.substr(0, 4) + '******' + this.props.value.substr(-2)
        };
        useInputField({ getValue: () => this.props.value || "" });
    }
}

PhoneFieldTree.template = "history_contact.PhoneFieldTree";
PhoneFieldTree.props = {
    ...standardFieldProps,
    placeholder: { type: String, optional: true },
};

PhoneFieldTree.displayName = _lt("Phone");
PhoneFieldTree.supportedTypes = ["char"];

PhoneFieldTree.extractProps = ({ attrs }) => {
    return {
        placeholder: attrs.placeholder,
    };
};

registry.category("fields").add("phone_tree", PhoneFieldTree);
