"""Part of odoo. See LICENSE file for full copyright and licensing details."""
import logging
from odoo.http import request
from odoo import http
# import pyodbc
from ..util import sync_asana
from datetime import datetime
import logging

import pytz
from odoo.addons.jwt_provider.JwtRequest import jwt_request
from odoo.exceptions import ValidationError
from odoo.http import request

from odoo import _
from odoo import http

_logger = logging.getLogger(__name__)

def check_field_require(field_require={}, payload={}):
    for field in field_require:
        if field not in payload.keys() or (
                type(payload.get(field)) != int and payload.get(field).replace(' ', '') == ''):
            result = {"status": 400, "message": "Data invalid! %s is required!!!" % field_require[field]}
            return result
    return ''


def response_500(exception=None):
    return {
        'status': 500,
        'message': exception or 'Server error'
    }


def response_400(message):
    return {
        'status': 400,
        'message': message
    }


def response_200(message=None):
    return {
        'status': 200,
        'message': message or 'SUCCESS!'
    }

_logger = logging.getLogger(__name__)


class SyncAsana(http.Controller):

    def sync_user_asana(self):
        print('___')
        # # Create a connection string
        # conn_str = sync_asana.conn_str
        # # Establish the connection
        # conn = pyodbc.connect(conn_str)
        # # Create a cursor from the connection
        # cursor = conn.cursor()
        # # Example: Execute a query
        # cursor.execute('SELECT * FROM AsanaUsers')
        # # Fetch the results
        # rows = cursor.fetchall()
        # for row in rows:
        #     print(row)
        #     user = request.env['res.users'].sudo().search(['|', ('email', '=', row[2]), ('login', '=', row[2])])
        #     if user and (not user.asana_gid or user.asana_gid != row[0]):
        #         user.asana_gid = row[0]
        # # Close the cursor and connection
        # cursor.close()
        # conn.close()

class APIMonitoringController(http.Controller):

    # @jwt_request.middlewares('jwt')
    @http.route("/api/v1/post-task", type="json", auth='public', csrf=False, cors='*', methods=['POST'])
    def api_create_task_monitoring(self, **payload):
        try:
            payload = request.get_json_data()
            values = {}
            for k, v in payload.items():
                values[k] = v
            field_require = {
                'mail_user': 'Mail user',
                'name': 'Name task',
                'description': 'Description',
            }
            check_result = check_field_require(field_require, payload)
            if check_result:
                return jwt_request.response(check_result)
            # _____________________________________________________________________
            user = request.env['res.users'].sudo().search(['|', ('email', '=', payload.get('mail_user')),
                                                                ('login', '=', payload.get('mail_user'))], limit=1)
            if not user:
                result = response_400("Mail user %s not exist!" % payload.get('mail_user'))
                return result
            project = False
            if payload.get('project_id'):
                project = request.env['project.project'].sudo().search([('id', '=', payload.get('project_id'))])
            vals = {
                'project_id': project if project else request.env.ref('pontusinc_project.project_api_monitoring').id,
                'name': payload.get('name'),
                'description': payload.get('description'),
                'user_ids':  [(6, 0, user.ids)]
            }
            task = request.env['project.task'].sudo().create([vals])
            result = response_200("SUCCESS!")
            result.update({"task_id": task.id})
            return result
        except Exception as ie:
            print(ie)
            result = response_500('Server error')
            return jwt_request.response_500(result)

