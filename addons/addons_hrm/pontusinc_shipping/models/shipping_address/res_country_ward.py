# -*- coding: utf-8 -*-
from ...util import api_category_vnpost
from odoo import fields, api, models, _
import requests

class CountryWard(models.Model):
    _inherit = "res.country.ward"


    def init(self):
        url = api_category_vnpost.URL_API_VNPOST + api_category_vnpost.get_all_commune
        headers = {
            'token': 'CCBM0a0WqkVPAvIDw3ph+03x9WPP4VgfwesmEa53gNqyvmcnbDoI/aqWaUYyo+h5ej6iUA5N9ZEjHfn9RsXvbnWdmz/XLInbxSO8aDeU8iMmzJDnrahqLIvUF9BQaSb9'
        }
        session = requests.Session()
        response = session.get(url, headers=headers)

        if response.status_code == 200:
            data = response.json()
            vals = []
            for rec in data:
                ward = self.search([('code', '=', rec.get('communeCode'))])
                if not ward:
                    district = self.env['res.country.district'].sudo().search([('code', '=', rec.get('districtCode'))])
                    if district:
                        vals.append({
                            'name': rec.get('communeName'),
                            'code': rec.get('communeCode'),
                            'district_id': district[0].id
                        })
            self.sudo().create(vals)
