/** @odoo-module **/

import { ImageField } from "@web/views/fields/image/image_field";
import { useInputField } from "@web/views/fields/input_field_hook";
import { useService } from "@web/core/utils/hooks";
const originalSetup = ImageField.prototype.setup;
import { useExternalListener } from "@odoo/owl";
// Extend the setup method of the WebClient
ImageField.prototype.setup = function () {
    originalSetup.call(this);
    this.action = useService("action");

};
ImageField.prototype.onClickSearch = function () {
    console.log('onClickSearch')
    var rpc = require('web.rpc');
    var self = this;
    var url = false
    if (this.lastURL){
        url = this.lastURL
    }else{
        url = this.getUrl(this.props.name)
    }
    rpc.query({
        model: "res.partner",
        method: 'search_imint_avatar',
        args: [this.props.record.data.id, url]
    })
    .then(function (res) {
        self.action.doAction(res)
    });
};

