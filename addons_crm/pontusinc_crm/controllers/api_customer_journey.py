import logging

from odoo import http
from odoo.http import request

from odoo.addons.jwt_provider.JwtRequest import jwt_request
from ..util import response

_logger = logging.getLogger(__name__)


class APICustomerJourney(http.Controller):

    # @jwt_request.middlewares('jwt')
    @http.route("/api/v1/get_info_partner", type="json", auth='public', csrf=False, cors='*', methods=['GET'])
    def api_get_info_partner(self, **payload):
        try:
            payload = request.get_json_data()
            values = {}
            for k, v in payload.items():
                values[k] = v
            field_require = {
                'partner_id': 'Partner ID',
            }
            check_result = response.check_field_require(field_require, payload)
            if check_result:
                return jwt_request.response(check_result)
            # _____________________________________________________________________
            partner = request.env['res.partner'].browse(payload['partner_id'])
            if not partner:
                result = {"status": 400, "message": "Data invalid! Partner does not exist!!!"}
                return jwt_request.response(result)
            else:
                value = partner.with_context(api_read_partner=True).read(
                    ['name', 'function', 'email', 'phone', 'mobile', 'vat', 'title'])
                result = response.response_200("SUCCESS!", value)
                return result
        except Exception as ie:
            print(ie)
            result = response.response_500('Server error', ie)
            return jwt_request.response_500(result)
        return jwt_request.response(payload)

    # @jwt_request.middlewares('jwt')
    @http.route("/api/v1/update_info_partner", type="json", auth='public', csrf=False, cors='*', methods=['POST'])
    def api_update_info_partner(self, **payload):
        try:
            payload = request.get_json_data()
            values = {}
            for k, v in payload.items():
                values[k] = v
            field_require = {
                'partner_id': 'Partner ID',
            }
            check_result = response.check_field_require(field_require, payload)
            if check_result:
                return jwt_request.response(check_result)
            # _____________________________________________________________________
            partner = request.env['res.partner'].browse(payload['partner_id'])
            if not partner:
                result = {"status": 400, "message": "Data invalid! Partner does not exist!!!"}
                return jwt_request.response(result)
            else:
                value_update = {
                    'partner_id': payload['partner_id'],
                }
                value_update.update(payload)
                request.env['update.partner'].sudo().create(value_update)
                result = response.response_200("SUCCESS!", "update success partner %s" % partner.name)
                return result
        except Exception as ie:
            print(ie)
            result = response.response_500('Server error', ie)
            return jwt_request.response_500(result)
        return jwt_request.response(payload)

    # @jwt_request.middlewares('jwt')
    @http.route("/api/v1/create-partner", type="json", auth='public', csrf=False, cors='*', methods=['POST'])
    def api_create_partner(self, **payload):
        try:
            payload = request.get_json_data()
            values = {}
            for k, v in payload.items():
                values[k] = v
            field_require = {
                'name': 'Name',
            }
            check_result = response.check_field_require(field_require, payload)
            if check_result:
                return jwt_request.response(check_result)
            # _____________________________________________________________________
            domain = []
            if payload.get('email'):
                domain += [('email', '=', payload.get('email'))]
            if payload.get('phone'):
                domain += ['|', ('phone', '=', payload.get('phone')), ('mobile', '=', payload.get('phone'))]
            if domain:
                partner = request.env['res.partner'].sudo().search(domain)
                if partner:
                    result = {"status": 400, "message": "Data invalid! Partner already exist!!!"}
                    return jwt_request.response(result)
            partner = request.env['res.partner'].sudo().create([payload])
            result = response.response_200("SUCCESS!", "Create success partner %s" % partner.name)
            return result
        except Exception as ie:
            print(ie)
            result = response.response_500('Server error', ie)
            return jwt_request.response_500(result)
        return jwt_request.response(payload)
