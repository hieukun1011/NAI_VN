# -*- coding: utf-8 -*-
import json

from odoo import http
from odoo.http import request
from datetime import datetime, timedelta

class ZaloControllers(http.Controller):


    @http.route('/zalo/authorize', auth='public', csrf=False)
    def index(self, **kw):
        record = http.request.env.ref('zalo_configuration.zalo_configuration').sudo()
        record.authorization_code = kw.get('code', '')
        record.access_token = ''
        record.refresh_token = ''
        record.get_access_token()
        return "Authorization Success!"