/** @odoo-module **/
var rpc = require('web.rpc');
import { useService } from "@web/core/utils/hooks";
import { ListController } from "@web/views/list/list_controller";
const { onWillStart, useComponent } = owl;

export function useUpdatePartnerButton() {
    const component = useComponent();
    const user = useService("user");
    const action = useService("action");
    component.onClickUpdateInfo = () => {
        var selection = []
        for (var i of component.model.root.selection) {
            selection.push(i.resId);
        }
        rpc.query({
            model: 'result.profiling',
            method: 'action_update_partner',
            args: [selection],
        }).then(() => {
            return component.actionService.doAction({
                    type: "ir.actions.act_window_close",
                });
        });
    };
    component.onClickClose = () => {
        return component.actionService.doAction({
            type: "ir.actions.act_window_close",
        });
    };
}
