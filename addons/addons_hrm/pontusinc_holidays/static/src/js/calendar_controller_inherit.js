odoo.define('@pontusinc_holidays/js/calendar_controller_inherit', async function (require) {
    'use strict';

    const { TimeOffCalendarController } = require('@hr_holidays/views/calendar/calendar_controller');
    const { FormViewDialog } = require('@web/views/view_dialogs/form_view_dialog');
    const { FormController } = require("@web/views/form/form_controller");
    const { Dialog } = require("@web/core/dialog/dialog");
    var rpc = require('web.rpc')

    const FormControllerMixin = {
        async saveButtonClicked(params = {}) {
            this.disableButtons();
            const record = this.model.root;
            let saved = false;
            if (this.props.saveRecord) {
                saved = await this.props.saveRecord(record, params);
            } else {
                saved = await record.save();
            }
            this.enableButtons();
            if (saved && this.props.onSave) {
                this.props.onSave(record, params);
            }
            const id = record.data.id ? record.data.id : null;
            const type_option = params.type_option ? 'send' : 'save';
            rpc.query({
                model: 'hr.leave',
                method: 'rpc_update_status',
                args: [id, type_option],
                });
            return saved;
        },
        async sendButtonClicked(params = {}) {
            this.saveButtonClicked({'type_option' : 'send'});
        }
    };
    const TimeOffCalendarControllerMixin = {
        newTimeOffRequest: function () {
            const context = {};
            if (this.employeeId) {
                context['default_employee_id'] = this.employeeId;
            }
            if (this.model.meta.scale == 'day') {
                context['default_date_from'] = serializeDate(
                    this.model.data.range.start.set({ hours: 7 }), "datetime"
                );
                context['default_date_to'] = serializeDate(
                    this.model.data.range.end.set({ hours: 19 }), "datetime"
                );
            }

            const a = this.displayDialog(FormViewDialog, {
                resModel: 'hr.leave',
                title: this.env._t('New Time Off'),
                viewId: this.model.formViewId,
                onRecordSaved: () => {
                    this.model.load();
                    this.env.timeOffBus.trigger('update_dashboard');
                },
                context: context,
            });
        }
    };
    FormViewDialog.template = "web.FormViewDialogs";
    Object.assign(FormController.prototype, FormControllerMixin);
    Object.assign(TimeOffCalendarController.prototype, TimeOffCalendarControllerMixin);

    return TimeOffCalendarController, FormController, FormViewDialog;
});

