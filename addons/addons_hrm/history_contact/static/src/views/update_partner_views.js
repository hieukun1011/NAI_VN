/** @odoo-module **/

import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";
import { useUpdatePartnerButton } from "@history_contact/views/update_partner_hook";
import { ListController } from "@web/views/list/list_controller";
import { listView } from "@web/views/list/list_view";

export class UpdateInfoPartnerListController extends ListController {
    setup() {
        console.log('UpdateInfoPartnerListController')
        super.setup();
        useUpdatePartnerButton();
    }
}

registry.category("views").add("update_info_partner", {
    ...listView,
    Controller: UpdateInfoPartnerListController,
    buttonTemplate: "UpdatePartnerRequestListView.buttons",
});

