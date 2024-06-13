/** @odoo-module **/
var rpc = require('web.rpc');
//var _t = core._t;
import { useService } from "@web/core/utils/hooks";
import { ListController } from "@web/views/list/list_controller";
const { onWillStart, useComponent } = owl;

export function useReportButton() {
    const component = useComponent();
    const user = useService("user");
    const action = useService("action");
    component.onClickReport = () => {
        return component.actionService.doAction({
            type: 'ir.actions.act_window',
            name: ('Timesheet - Penalty calculation'),
            res_model: 'popup.report.timesheet',
            views: [[false, 'form']],
            view_mode: 'form',
            target: 'new',
        });
//        rpc.query({
//            model: 'timesheet.penalty.calculation',
//            method: 'cron_report_timesheet_penalty_calculation',
//            args: [1],
//        }).then(() => {
//            return component.actionService.doAction({
//                    'type': 'ir.actions.client',
//                    'tag': 'reload',
//                });
//        });
    };
}
