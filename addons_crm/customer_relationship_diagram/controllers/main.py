# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.exceptions import AccessError
from odoo.http import request


class CustomerRelationshipDiagramController(http.Controller):
    _managers_level = 5  # FP request

    def _check_partner(self, partner_id, **kw):
        if not partner_id:  # to check
            return None
        partner_id = int(partner_id)

        if 'allowed_company_ids' in request.env.context:
            cids = request.env.context['allowed_company_ids']
        else:
            cids = [request.env.company.id]

        Partner = request.env['res.partner'].with_context(allowed_company_ids=cids)
        # check and raise
        if not Partner.check_access_rights('read', raise_exception=False):
            return None
        try:
            Partner.browse(partner_id).check_access_rule('read')
        except AccessError:
            return None
        else:
            return Partner.browse(partner_id)

    def _prepare_partner_data(self, partner):
        return dict(
            id=partner.id,
            name=partner.name,
            link='/mail/view?model=%s&res_id=%s' % ('res.partner', partner.id,),
            partner_rank=partner.function or '',
            direct_sub_count=len(partner.child_presenter_ids - partner),
            indirect_sub_count=partner.child_all_count,
        )

    @http.route('/customer_360/get_redirect_model', type='json', auth='user')
    def get_redirect_model(self):
        return 'res.partner'

    @http.route('/customer_360/get_customer_relationship_diagram', type='json', auth='user')
    def get_customer_relationship_diagram(self, partner_id, **kw):

        partner = self._check_partner(partner_id, **kw)
        if not partner:  # to check
            return {
                'managers': [],
                'children': [],
            }

        # compute employee data for org chart
        ancestors, current = request.env['res.partner'].sudo(), partner.sudo()
        while current.presenter_id and len(ancestors) < self._managers_level+1 and current != current.presenter_id:
            ancestors += current.presenter_id
            current = current.presenter_id

        values = dict(
            self=self._prepare_partner_data(partner),
            managers=[
                self._prepare_partner_data(ancestor)
                for idx, ancestor in enumerate(ancestors)
                if idx < self._managers_level
            ],
            managers_more=len(ancestors) > self._managers_level,
            children=[self._prepare_partner_data(child) for child in partner.child_presenter_ids if child != partner_id],
        )
        values['managers'].reverse()
        return values

    @http.route('/customer_360/get_subordinates', type='json', auth='user')
    def get_subordinates(self, partner_id, subordinates_type=None, **kw):

        partner = self._check_partner(partner_id, **kw)
        if not partner:  # to check
            return {}

        if subordinates_type == 'direct':
            res = (partner.child_presenter_ids - partner).ids
        elif subordinates_type == 'indirect':
            res = (partner.subordinate_ids - partner.child_presenter_ids).ids
        else:
            res = partner.subordinate_ids.ids

        return res
