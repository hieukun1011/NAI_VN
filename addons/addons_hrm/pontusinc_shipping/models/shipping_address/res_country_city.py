# -*- coding: utf-8 -*-
import requests
from odoo import fields, api, models, _
from ...util import api_category_vnpost
import re

class CountryCity(models.Model):
    _inherit = "res.country.state"

    area_id = fields.Many2one('area.shipping', string='Area')

    def init(self):
        url = api_category_vnpost.URL_API_VNPOST + api_category_vnpost.get_all_city
        headers = {
            'token': 'CCBM0a0WqkVPAvIDw3ph+03x9WPP4VgfwesmEa53gNqyvmcnbDoI/aqWaUYyo+h5ej6iUA5N9ZEjHfn9RsXvbnWdmz/XLInbxSO8aDeU8iMmzJDnrahqLIvUF9BQaSb9'
        }
        session = requests.Session()
        response = session.get(url, headers=headers)

        if response.status_code == 200:
            data = response.json()
            for rec in data:
                modified_name = re.sub(r'\b(Tỉnh |TP\. )\b', '', rec.get('provinceName'))
                city = self.search([('name', 'ilike', modified_name)])
                if city:
                    city.code_vnpost = rec.get('provinceCode')
