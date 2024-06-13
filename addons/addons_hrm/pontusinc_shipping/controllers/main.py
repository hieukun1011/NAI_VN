"""Part of odoo. See LICENSE file for full copyright and licensing details."""
import logging

from odoo.addons.jwt_provider.JwtRequest import jwt_request
from odoo.http import request

from odoo import http
from ..util import response, log_ulti

_logger = logging.getLogger(__name__)


class WebhookAutoUpdateStateShipping(http.Controller):

    @http.route("/api/v1/update-state-waybill", type="json", auth='public', csrf=False, cors='*', methods=['POST'])
    def api_update_state_waybill(self, **payload):
        try:
            payload = request.get_json_data()
            for data in payload:
                if data.get('originalId'):
                    shipping = self.env['shipping.waybill'].sudo().search(
                        [('code_shipping', '=', data.get('originalId'))])
                    if shipping:
                        vals = {
                            'state_id': self.env['shipping.state'].sudo().search([('code', '=', data.get('status')),
                                                                                  ('platform_id', '=', self.env.ref(
                                                                                      'pontusinc_shipping.shipping_platform_vnpost').id)]),

                        }
        except Exception as ie:
            result = response.response_500('Server error', ie)
            return jwt_request.response_500(result)
        return jwt_request.response(payload)
