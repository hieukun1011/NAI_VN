"""Part of odoo. See LICENSE file for full copyright and licensing details."""

import logging

from odoo.addons.jwt_provider.JwtRequest import jwt_request

from ..util import response, log_ulti

try:
    from werkzeug.utils import send_file
except ImportError:
    from odoo.tools._vendor.send_file import send_file

from odoo import http
from odoo.exceptions import UserError
from odoo.http import request
from odoo.tools.image import image_guess_size_from_field_name

_logger = logging.getLogger(__name__)


class HistoryContactController(http.Controller):

    @jwt_request.middlewares('jwt')
    @http.route("/api/v1/get-aciton-partner", type="json", auth='public', csrf=False, cors='*', methods=['GET'])
    def api_get_action_partner(self, **payload):
        try:
            action = request.env['action.partner'].sudo().search([])
            result = response.response_200("SUCCESS!", action.read(['code', 'name']))
            return result
        except Exception as ie:
            result = response.response_500('Server error', ie)
            return jwt_request.response_500(result)
        return jwt_request.response(payload)

    @jwt_request.middlewares('jwt')
    @http.route("/api/v1/get-history-action-partner", type="json", auth='public', csrf=False, cors='*', methods=['GET'])
    def api_get_history_action_partner(self, **payload):
        try:
            payload = request.get_json_data()
            if not payload.get('phone') and not payload.get('email'):
                result = {"status": 400, "message": "Data invalid! Phone or Email is required!!!"}
                return result
            domain = []
            if payload.get('phone'):
                phone = log_ulti.convert_sdt(payload.get('phone'))
                domain += ['|', ('phone', '=', phone), ('mobile', '=', phone)]
            if payload.get('email'):
                domain += [('email', '=', payload.get('email'))]
            partner = request.env['res.partner'].sudo().search(domain, limit=1)
            if not partner:
                result = {"status": 400, "message": "Data invalid! Phone or Email does not exist!!!"}
                return jwt_request.response(result)
            data = []
            for rec in partner.history_ids:
                data.append({
                    'id': rec.id,
                    'partner_detail': {
                        'id': rec.partner_id.id,
                        'name': rec.partner_id.name
                    },
                    'action_detail': {
                        'id': rec.action_id.id,
                        'name': rec.action_id.name
                    },
                    'location': rec.location,
                    'description': rec.description,
                    'create_date': rec.create_date,
                })
            result = response.response_200("SUCCESS!", data)
            return result
        except Exception as ie:
            result = response.response_500('Server error', ie)
            return jwt_request.response_500(result)
        return jwt_request.response(payload)

    @jwt_request.middlewares('jwt')
    @http.route("/api/v1/post-aciton-partner", type="json", auth='public', csrf=False, cors='*', methods=['POST'])
    def api_post_action_partner(self, **payload):
        try:
            payload = request.get_json_data()
            values = {}
            _logger.info(payload)
            for k, v in payload.items():
                values[k] = v
            field_require = {
                'name': 'Name',
                'action_id': 'Action partner',
                'target_location': 'Target location',
            }
            check_result = response.check_field_require(field_require, payload)
            if check_result:
                return jwt_request.response(check_result)
            # _____________________________________________________________________
            action = request.env['action.partner'].sudo().search([('id', '=', payload.get('action_id'))], limit=1)
            if not action:
                result = {"status": 400, "message": "Data invalid! Action does not exist!!!"}
                return jwt_request.response(result)
            if payload.get('id'):
                record_history = request.env['history.contact'].sudo().browse(payload.get('id'))
                if record_history.read():
                    record_history.sudo().write({
                        'action_id': action.id,
                        'location': payload.get('target_location'),
                        'description': payload.get('source_description'),
                        'create_date': payload.get('source_created_time'),
                        'source_url': payload.get('source_url'),
                        'platform_id': payload.get('source_platform'),
                        'employee_id': payload.get('source_employee'),
                        'updated_time': payload.get('source_updated_time'),
                    })
                    result = response.response_200("SUCCESS!")
                    return result
                else:
                    result = {"status": 400, "message": "Data invalid! Record ID does not exist!!!"}
                    return jwt_request.response(result)
            if not payload.get('target_mail') and not payload.get('target_phone'):
                result = {"status": 400, "message": "Data invalid! Phone or Email is required!!!"}
                return jwt_request.response(result)
            else:
                domain = []
                if payload.get('target_phone'):
                    phone = log_ulti.convert_sdt(payload.get('target_phone'))
                    domain += ['|', ('phone', 'ilike', phone), ('mobile', 'ilike', phone)]
                if payload.get('target_mail'):
                    domain += [('email', 'ilike', payload.get('target_mail'))]
                _logger.info(domain)
                partner = request.env['res.partner'].sudo().search(domain, limit=1)
            if partner:
                history_id = request.env['history.contact'].sudo().create({
                    'partner_id': partner.id,
                    'action_id': action.id,
                    'location': payload.get('target_location'),
                    'description': payload.get('source_description'),
                    'created_time': payload.get('source_created_time'),
                    'source_url': payload.get('source_url'),
                    'platform_id': payload.get('source_platform'),
                    'employee_id': payload.get('source_employee'),
                })
                result = response.response_200("SUCCESS!", history_id.id)
                return result
            else:
                vals = {
                    'name': payload['name'],
                    'phone': payload.get('target_phone'),
                    'nick_name': payload.get('nick_name'),
                    'email': payload.get('target_mail'),
                    # 'birthday': payload.get('birthday'),
                    'source_name': payload.get('source_platform')
                }
                partner = request.env['res.partner'].sudo().create([vals])
                result = response.response_200("SUCCESS!", "Create success partner %s" % partner.name)
                return result
        except Exception as ie:
            print(ie)
            result = response.response_500('Server error', ie)
            return jwt_request.response_500(result)
        return jwt_request.response(payload)


class Binary(http.Controller):
    @http.route(['/web/image',
                 '/web/image/<string:xmlid>',
                 '/web/image/<string:xmlid>/<string:filename>',
                 '/web/image/<string:xmlid>/<int:width>x<int:height>',
                 '/web/image/<string:xmlid>/<int:width>x<int:height>/<string:filename>',
                 '/web/image/<string:model>/<int:id>/<string:field>',
                 '/web/image/<string:model>/<int:id>/<string:field>/<string:filename>',
                 '/web/image/<string:model>/<int:id>/<string:field>/<int:width>x<int:height>',
                 '/web/image/<string:model>/<int:id>/<string:field>/<int:width>x<int:height>/<string:filename>',
                 '/web/image/<int:id>',
                 '/web/image/<int:id>/<string:filename>',
                 '/web/image/<int:id>/<int:width>x<int:height>',
                 '/web/image/<int:id>/<int:width>x<int:height>/<string:filename>',
                 '/web/image/<int:id>-<string:unique>',
                 '/web/image/<int:id>-<string:unique>/<string:filename>',
                 '/web/image/<int:id>-<string:unique>/<int:width>x<int:height>',
                 '/web/image/<int:id>-<string:unique>/<int:width>x<int:height>/<string:filename>'], type='http',
                auth="public")
    # pylint: disable=redefined-builtin,invalid-name
    def content_image(self, xmlid=None, model='ir.attachment', id=None, field='raw',
                      filename_field='name', filename=None, mimetype=None, unique=False,
                      download=False, width=0, height=0, crop=False, access_token=None,
                      nocache=False):
        try:
            record = request.env['ir.binary'].sudo()._find_record(xmlid, model, id and int(id), access_token)
            stream = request.env['ir.binary'].sudo()._get_image_stream_from(
                record, field, filename=filename, filename_field=filename_field,
                mimetype=mimetype, width=int(width), height=int(height), crop=crop,
            )
        except UserError as exc:
            if download:
                raise request.not_found() from exc
            # Use the ratio of the requested field_name instead of "raw"
            if (int(width), int(height)) == (0, 0):
                width, height = image_guess_size_from_field_name(field)
            record = request.env.ref('web.image_placeholder').sudo()
            stream = request.env['ir.binary'].sudo()._get_image_stream_from(
                record, 'raw', width=int(width), height=int(height), crop=crop,
            )

        send_file_kwargs = {'as_attachment': download}
        if unique:
            send_file_kwargs['immutable'] = True
            send_file_kwargs['max_age'] = http.STATIC_CACHE_LONG
        if nocache:
            send_file_kwargs['max_age'] = None

        res = stream.get_response(**send_file_kwargs)
        res.headers['Content-Security-Policy'] = "default-src 'none'"
        return res
