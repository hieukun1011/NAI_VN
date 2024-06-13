/** @odoo-module */

import { registry} from '@web/core/registry';
import { DynamicDashboardTile} from './DynamicDashboardTile'
import { DynamicDashboardChart} from './DynamicDashboardChart'
import { useService } from "@web/core/utils/hooks";
const { Component, mount} = owl
export class DynamicDashboard extends Component {
    setup(){
        this.action = useService("action");
        this.rpc = this.env.services.rpc
        this.renderDashboard()
    }
    async renderDashboard() {
        const action = this.action
        const rpc = this.rpc
        await this.rpc('/get/values', {'action_id': this.props.actionId}).then(function(response){
            self.$('.o_iframe').attr('src', response);
        })
    }
}
DynamicDashboard.template = "owl.dynamic_dashboard"
registry.category("actions").add("owl.dynamic_dashboard", DynamicDashboard)
