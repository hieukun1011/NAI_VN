/** @odoo-module */

import { Field } from '@web/views/fields/field';
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { usePopover } from "@web/core/popover/popover_hook";
import { onPartnerSubRedirect } from './hooks';

const { Component, onWillStart, onWillRender, useState } = owl;

function useUniquePopover() {
    const popover = usePopover();
    let remove = null;
    return Object.assign(Object.create(popover), {
        add(target, component, props, options) {
            if (remove) {
                remove();
            }
            remove = popover.add(target, component, props, options);
            return () => {
                remove();
                remove = null;
            };
        },
    });
}

export class CustomerRelationshipDiagram extends Field {
    async setup() {
        super.setup();

        this.rpc = useService('rpc');
        this.orm = useService('orm');
        this.actionService = useService("action");
        this.popover = useUniquePopover();

        this.jsonStringify = JSON.stringify;

        this.state = useState({'partner_id': null});
        this.lastParent = null;
        this._onPartnerSubRedirect = onPartnerSubRedirect();

        onWillStart(this.handleComponentUpdate.bind(this));
        onWillRender(this.handleComponentUpdate.bind(this));
    }

    /**
     * Called on start and on render
     */
    async handleComponentUpdate() {
        console.log('handleComponentUpdate')
        this.partner = this.props.record.data;
        // the widget is either dispayed in the context of a hr.employee form or a res.users form
        this.state.partner_id = this.partner.partner_ids !== undefined ? this.partner.partner_ids.resIds[0] : this.partner.id;
        const manager = this.partner.presenter_id;
        const forceReload = this.lastRecord !== this.props.record || this.lastParent != manager;
        this.lastParent = manager;
        this.lastRecord = this.props.record;
        await this.fetchPartnerData(this.state.partner_id, forceReload);
    }

    async fetchPartnerData(partnerId, force = false) {
        console.log('fetchEmployeeData')
        if (!partnerId) {
            this.managers = [];
            this.children = [];
            if (this.view_partner_id) {
                this.render(true);
            }
            this.view_partner_id = null;
        } else if (partnerId !== this.view_partner_id || force) {
            this.view_partner_id = partnerId;
            var orgData = await this.rpc(
                '/customer_360/get_customer_relationship_diagram',
                {
                    partner_id: partnerId,
                    context: Component.env.session.user_context,
                }
            );
            if (Object.keys(orgData).length === 0) {
                orgData = {
                    managers: [],
                    children: [],
                }
            }
            this.managers = orgData.managers;
            this.children = orgData.children;
            this.managers_more = orgData.managers_more;
            this.self = orgData.self;
            this.render(true);
        }
    }

    _onOpenPopover(event, partner) {
        console.log('_onOpenPopover')
        this.popover.add(
            event.currentTarget,
            this.constructor.components.Popover,
            {partner},
            {closeOnClickAway: true}
        );
    }

    /**
     * Redirect to the employee form view.
     *
     * @private
     * @param {MouseEvent} event
     * @returns {Promise} action loaded
     */
    async _onPartnerRedirect(partnerId) {
        const action = await this.orm.call('res.partner', 'get_formview_action', [partnerId]);
        this.actionService.doAction(action);
    }

    async _onPartnerMoreManager(managerId) {
        await this.fetchPartnerData(managerId);
        this.state.partner_id = managerId;
    }
}

CustomerRelationshipDiagram.template = 'customer_relationship_diagram.customer_relationship_diagram';

registry.category("fields").add("customer_relationship_diagram", CustomerRelationshipDiagram);
