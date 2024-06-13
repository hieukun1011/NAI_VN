/** @odoo-module */

import { registry } from "@web/core/registry";

import { formatDate } from "@web/core/l10n/dates";

import { RankX2ManyField } from "./common_one2many";
import { CommonRankListRenderer } from "../views/rank_list_renderer";

export class LogRankListRenderer extends CommonRankListRenderer {
    get groupBy() {
        return 'rank_id';
    }

    get colspan() {
        if (this.props.activeActions) {
            return 3;
        }
        return 2;
    }

    formatDate(date) {
        return formatDate(date);
    }

    setDefaultColumnWidths() {}
}
LogRankListRenderer.template = 'pontusinc_crm.LogRankListRenderer';
LogRankListRenderer.rowsTemplate = "pontusinc_crm.LogRankListRenderer.Rows";
LogRankListRenderer.recordRowTemplate = "pontusinc_crm.LogRankListRenderer.RecordRow";


export class LogRankX2ManyField extends RankX2ManyField {}
LogRankX2ManyField.components = {
    ...RankX2ManyField.components,
    ListRenderer: LogRankListRenderer,
};

registry.category("fields")
    .add("log_rank_one2many", LogRankX2ManyField);
