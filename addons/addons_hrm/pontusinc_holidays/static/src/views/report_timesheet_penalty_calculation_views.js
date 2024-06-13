/** @odoo-module **/

import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";
import { useReportButton } from "@pontusinc_holidays/views/report_timesheet_penalty_calculation_hook";
import { ListController } from "@web/views/list/list_controller";
import { listView } from "@web/views/list/list_view";

export class ReportTimesheetPenaltyCalculationListController extends ListController {
    setup() {
        console.log('ReportTimesheetPenaltyCalculationListController')
        super.setup();
        useReportButton();
    }
}

registry.category("views").add("report_timesheet_penalty_calculation", {
    ...listView,
    Controller: ReportTimesheetPenaltyCalculationListController,
    buttonTemplate: "ReportTimesheetPenaltyCalculationListView.buttons",
});

