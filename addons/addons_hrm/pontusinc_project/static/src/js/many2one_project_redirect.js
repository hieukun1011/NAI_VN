/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Many2OneField } from "@web/views/fields/many2one/many2one_field";

export class Many2OneClickable extends Many2OneField {
    setup() {
        super.setup();
    }
    onClick(ev) {
        if (this.props.canOpen && this.props.readonly) {
            ev.stopPropagation();
            this.openAction(ev);
        }
    }
    async openAction(ev) {
        if (this.props.name === 'project_id' && this.props.value) {
            const projectId = this.props.value[0];
            if (projectId) {
                this.action.doAction({type: 'ir.actions.act_window',
                                    res_model: 'project.task',
                                    view_mode: 'tree',
                                    name: this.props.value[1],
                                    view_type: 'tree',
                                    views: [[false, 'tree'], [false, 'form']],
                                    target: 'current',
                                    domain:  [['project_id', '=', projectId]],
                                    res_id: false,
                                    })
            }
        } else {
            const action = await this.orm.call(this.relation, "get_formview_action", [[this.resId]], {
            context: this.context,
        });
        await this.action.doAction(action);
        }
    }


    get className() {
        // Append a class for styling if necessary
        return super.className + ' custom-many2one-clickable';
    }
}

Many2OneClickable.template = 'web.Many2OneField';
Many2OneClickable.props = {
    ...Many2OneField.props,
    options: { type: Object, optional: true },
};

registry.category("fields").add("many2one_clickable", Many2OneClickable);
