/** @odoo-module */

import { X2ManyField } from "@web/views/fields/x2many/x2many_field";
import { registry } from "@web/core/registry";

import { CommonRankListRenderer } from "../views/rank_list_renderer";


export class RankListRenderer extends CommonRankListRenderer {
    get groupBy() {
        return 'rank_id';
    }

    calculateColumnWidth(column) {
        if (column.name != 'level_id') {
            return {
                type: 'absolute',
                value: '90px',
            }
        }

        return super.calculateColumnWidth(column);
    }
}
RankListRenderer.template = 'pontusinc_crm.RankListRenderer';

export class RankX2ManyField extends X2ManyField {
    async onAdd({ context, editable } = {}) {
        const PartnerId = this.props.record.resId;
        return super.onAdd({
            editable,
            context: {
                ...context,
                default_partner_id: PartnerId,
            }
        });
    }
}
RankX2ManyField.components = {
    ...X2ManyField.components,
    ListRenderer: RankListRenderer,
};

registry.category("fields").add("rank_one2many", RankX2ManyField);
