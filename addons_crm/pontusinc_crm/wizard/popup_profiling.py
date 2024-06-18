import json
import re

import requests
from bs4 import BeautifulSoup
from odoo.exceptions import ValidationError

from odoo import models, fields, api, _
from ..util import header_api
from ..util.log_ulti import LogUtil


class PopupProfiling(models.TransientModel):
    _name = 'search.profiling'
    _description = 'Popup Profiling'

    tag_ids = fields.Many2one('tag.profiling', string='Field search')
    input = fields.Char('Input')
    partner_id = fields.Many2one('res.partner', string='Partner')
    field_search = fields.Many2many('ir.model.fields', string='Field search')

    @api.onchange('tag_ids')
    def default_input(self):
        self.ensure_one()
        if self.tag_ids:
            self.input = self.env.context.get(self.tag_ids.name.lower())

    def get_token(self, user_name, password):
        self.ensure_one()
        url = header_api.URL_TOKEN
        headers = header_api.headers
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

    def action_search_profiling(self):
        self.ensure_one()
        token = self.get_token('erp.icomm', 'abcd@123')
        if not token:
            raise ValidationError(_('Error! Unable to get search profiling login token'))
        else:
            url = header_api.URL_SEARCH_PROFILING
            headers = header_api.headers
            headers.update({
                "accept-language": 'vi,en-US;q=0.9,en;q=0.8',
                "authorization": token.get('token_type') + ' ' + token.get('access_token'),
                "cookie": 'token=' + token.get('access_token') + '; token_refresh=' + token.get(
                    'refresh_token') + '; app=profi',
                "referer": "https://staging.pontusinc.com/profi/research-online-people/",
                "sec-ch-ua": '"Google Chrome";v="119", "Chromium";v="119", "Not?A_Brand";v="24"',
                "sec-ch-ua-platform": '"Windows"',
                "sec-fetch-site": 'same-origin',
                "user-agent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            })
            if 'span' in self.input:
                input_str = BeautifulSoup(self.input, 'html.parser').find('span').text
            elif 'p' in self.input:
                input_str = BeautifulSoup(self.input, 'html.parser').find('p').text
            else:
                input_str = self.input
            template = {
                "q": input_str,
                "fields": [i.name for i in self.tag_ids],
                "draw": 1,
                "columns": [{
                    "data": "0",
                    "name": "",
                    "searchable": True,
                    "orderable": False,
                    "search": {
                        "value": "",
                        "regex": False}
                }],
                "order": [{
                    "column": 0,
                    "dir": 0
                }],
                "start": 0,
                "length": 20,
                "search": {
                    "value": "",
                    "regex": False
                }
            }
            session = requests.Session()
            response = session.post(url, data=json.dumps(template), headers=headers)
            if response.status_code == 200:
                data = response.json()  # Dữ liệu trả về từ API
                if data.get('result'):
                    value_result = []
                    value_log = []
                    for rec in data.get('result').get('data'):
                        pattern = re.compile(r'<b>([^<]+)</b>:\s*<span class=\'normal\'>([^<]+)</span>')
                        matches = pattern.findall(rec.get('highlight'))
                        for key, value in matches:
                            value_result.append({
                                'name': key,
                                'detail': value,
                                'partner_id': self.partner_id.id
                            })
                            value_log.append({
                                'name': key,
                                'detail': value
                            })
                        # if 'CheckinLocationNames' in dict_data.keys():
                        #     LogUtil.create_log_history_partner(self=self.partner_id, action=self.env.ref(
                        #         'history_contact.action_partner_checkin'), location=dict_data['CheckinLocationNames'])
                    self.partner_id.write({
                        'search_profiling': value_log
                    })
                    result = self.env['result.profiling'].sudo().create(value_result)
                    return self.action_open_popup_result_profiling(result)
            else:
                raise ValidationError(
                    _("No further information is available %s: %s" % ([i.name for i in self.tag_ids], input_str)))

    def action_open_popup_result_profiling(self, result):
        tree_id = self.env.ref('pontusinc_crm.popup_result_profiling_tree_view').id
        return {
            'name': _("Result profiling"),
            'type': 'ir.actions.act_window',
            'view_mode': 'tree',
            'views': [(tree_id, 'tree')],
            'res_model': 'result.profiling',
            'target': 'new',
            'domain': [('id', 'in', result.ids)],
        }


class ResultProfiling(models.TransientModel):
    _name = 'result.profiling'
    _description = 'Result Profiling'

    partner_id = fields.Many2one('res.partner', string='Partner')
    name = fields.Char('Name')
    detail = fields.Char('Detail')

    def action_update_partner(self):
        if self.partner_id:
            partner = self.partner_id
            vals = {}
            for record in self:
                if record.name == 'DisplayName':
                    vals['name'] = record.detail
                elif record.name == 'FBId':
                    vals['facebook_id'] = record.detail
                elif record.name == 'Email':
                    vals['email'] = record.detail
                elif record.name == 'Phones':
                    vals['phone'] = record.detail
                    vals['mobile'] = record.detail
                elif record.name == 'CompanyNames':
                    vals['company_name'] = record.detail
                elif record.name == 'SchoolNames':
                    vals['school_name'] = record.detail
                elif record.name == 'Province':
                    vals['province'] = record.detail
                elif record.name == 'Hometown':
                    vals['hometown'] = record.detail
                elif record.name == 'CheckinLocationNames':
                    vals['checkin_location'] = record.detail
            print(vals)
            partner.write(vals)

    def close_popup(self):
        return {'type': 'ir.actions.act_window_close'}