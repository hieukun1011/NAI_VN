# -*- coding: utf-8 -*-
from ...util import api_category_vnpost
from odoo import fields, api, models, _
import requests

class CountryDistrict(models.Model):
    _inherit = "res.country.district"

    def init(self):
        url = api_category_vnpost.URL_API_VNPOST + api_category_vnpost.get_all_district
        headers = {
            'token': 'CCBM0a0WqkVPAvIDw3ph+03x9WPP4VgfwesmEa53gNqyvmcnbDoI/aqWaUYyo+h5ej6iUA5N9ZEjHfn9RsXvbnWdmz/XLInbxSO8aDeU8iMmzJDnrahqLIvUF9BQaSb9'
        }
        session = requests.Session()
        response = session.get(url, headers=headers)

        if response.status_code == 200:
            data = response.json()
            vals = []
            for rec in data:
                district = self.search([('code', '=', rec.get('districtCode'))])
                if not district:
                    city = self.env['res.country.state'].sudo().search([('code_vnpost', '=', rec.get('provinceCode'))])
                    if city:
                        vals.append({
                            'name': rec.get('districtName'),
                            'code': rec.get('districtCode'),
                            'state_id': city[0].id
                        })
            self.sudo().create(vals)

