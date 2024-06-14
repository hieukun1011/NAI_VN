# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU AFFERO
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU AFFERO GENERAL PUBLIC LICENSE (AGPL v3) for more details.
#
#    You should have received a copy of the GNU AFFERO GENERAL PUBLIC LICENSE
#    (AGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import http
from odoo.http import request
import requests
import json
# Get token search profiling
URL_TOKEN = 'https://staging.pontusinc.com/api/admin-mgt/v1/account/login_v2'

# Search profiling
URL_SEARCH_PROFILING = 'https://staging.pontusinc.com/api/profiling/v1/home/find'

# Headers API
headers_default = {
    'authority': 'staging.pontusinc.com',
    'accept': 'application/json, text/plain, */*',
    'content-type': 'application/json;charset=UTF-8',
    'pragma': 'no-cache',
    'sec-ch-ua-mobile': '?0',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'origin': 'https://staging.pontusinc.com',
}


class DynamicDashboard(http.Controller):
    """
    This is the class DynamicDashboard which is the subclass of the class
    http.Controller
    """

    @http.route('/create/tile', type='json', auth='user')
    def tile_creation(self, **kw):
        """This is the method to create the tile when create on the button
        ADD BLOCK"""
        tile_type = kw.get('type')
        action_id = kw.get('action_id')
        request.env['dashboard.block'].get_dashboard_vals(action_id)
        tile_id = request.env['dashboard.block'].sudo().create({
            'name': 'New Block',
            'type': tile_type,
            'tile_color': '#1f6abb',
            'text_color': '#FFFFFF',
            'fa_icon': 'fa fa-money',
            'fa_color': '#132e45',
            'edit_mode': True,
            'client_action': int(action_id),
        })
        return {'id': tile_id.id, 'name': tile_id.name, 'type': tile_type, 'icon': 'fa fa-money',
                'color': '#1f6abb',
                'tile_color': '#1f6abb',
                'text_color': '#FFFFFF',
                'icon_color': '#1f6abb'}

    @http.route('/get/values', type='json', auth='user')
    def get_value(self, **kw):
        """This is the method get_value which will get the records inside the
        tile"""
        action_id = kw.get('action_id')
        # datas = request.env['dashboard.block'].get_dashboard_vals(action_id)
        # data = request.env['dashboard.menu'].read_embed_code(action_id)
        user_social_care = request.env['user.social.care'].sudo().search([('user_id', '=', request.env.uid)], limit=1)
        token = self.get_token(user_social_care.login, user_social_care.password)
        return "https://staging.pontusinc.com/customer360/fanList?token=" + token['access_token']


    def get_token(self, user_name, password):
        url = URL_TOKEN
        headers = headers_default
        headers.update({
            'accept-language': 'vi,en-US;q=0.9,en;q=0.8',
            'cookie': 'token_refresh=',
            'loginusername': 'undefined',
            'referer': 'https://staging.pontusinc.com/login?fromLogout=true',
            'sec-ch-ua': '"Google Chrome";v="119", "Chromium";v="119", "Not?A_Brand";v="24"',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        })
        template = {
            'username': user_name,
            'password': password,
        }
        session = requests.Session()
        response = session.post(url, data=json.dumps(template), headers=headers)

        if response.status_code == 200:
            data = response.json()
            return data.get('result')
        else:
            return False
