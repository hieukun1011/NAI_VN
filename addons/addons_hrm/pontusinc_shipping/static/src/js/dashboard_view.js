odoo.define('crm_dashboard.CRMDashboard', function (require) {
    'use strict';

    var AbstractAction = require('web.AbstractAction');
    var ajax = require('web.ajax');
    var core = require('web.core');
    var rpc = require('web.rpc');
    var web_client = require('web.web_client');
    var session = require('web.session');
    var _t = core._t;
    var QWeb = core.qweb;
    var self = this;
    var currency;
    var DashBoard = AbstractAction.extend({
        contentTemplate: 'Shippingdashboard',
        events: {},

        init: function(parent, context) {
            this._super(parent, context);
            this.upcoming_events = [];
            this.current_lang=[];
            this.dashboards_templates = ['LoginUser','Managercrm',];
            this.login_employee = [];
        },

        willStart: function(){
            var self = this;
            this.login_employee = {};
            return this._super()
            .then(function() {
                return $.when();
            });
        },

        start: function() {
            var self = this;
            this.set("title", 'Dashboard');
            return this._super().then(function() {
                self.render_dashboards();
                self.$el.parent().addClass('oe_background_grey');
            });
        },

        render_dashboards: function() {
            var self = this;
            var templates = ['LoginUser', 'Managercrm']
            _.each(templates, function(template) {
                self.$('.o_hr_dashboard').append(QWeb.render(template, {widget: self}));
            });
        },

    });

    core.action_registry.add('shipping_dashboard', DashBoard);
    return DashBoard;
});