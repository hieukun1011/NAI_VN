/** @odoo-module **/
import { PhoneField } from "@web/views/fields/phone/phone_field";
import { useInputField } from "@web/views/fields/input_field_hook";
import { useService } from "@web/core/utils/hooks";
const originalSetup = PhoneField.prototype.setup;
// Extend the setup method of the WebClient
PhoneField.prototype.setup = function () {
    originalSetup.call(this);
    if (this.props.value){
        this.props.value_data = this.props.value.substr(0, 4) + '******' + this.props.value.substr(-2);
    }
    useInputField({ getValue: () => this.props.value || "" });
    this.action = useService("action");
};

PhoneField.prototype.SearchprofilingHref = function () {
    var rpc = require('web.rpc');
    var self = this;
    rpc.query({
        model: "res.partner",
        method: 'action_search_profiling',
        args: [this.props.record.data.id, this.props.name, this.props.value]
    })
    .then(function (res) {
        if (typeof(res) === 'string'){
            alert(res);
        }else{
            self.action.doAction(res)
        }
    });
};


