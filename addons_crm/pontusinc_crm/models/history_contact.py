import json
import re
from datetime import datetime

import requests
from odoo.exceptions import ValidationError
from odoo.http import request
from psycopg2 import sql

from odoo import models, fields, api, _
from ..util import header_api
from ..util import log_ulti
import urllib.parse

from urllib.parse import quote

class HistoryContact(models.Model):
    _name = 'history.contact'
    _description = 'History action contact'

    partner_id = fields.Many2one('res.partner', string='Partner')
    action_id = fields.Many2one('action.partner', string='Touchpoint')
    location = fields.Char('Location')
    description = fields.Char('Description')
    source_url = fields.Char('Source URL')
    platform_id = fields.Char('Platform')
    employee_id = fields.Char('Employee')
    updated_time = fields.Datetime('Updated time')
    created_time = fields.Datetime('Created time')

    def write(self, vals):
        if not vals.get('updated_time'):
            vals['updated_time'] = vals.get('write_date')
        else:
            vals['updated_time'] = datetime.strptime(vals['updated_time'], "%d-%m-%Y %H:%M:%S")
        return super().write(vals)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('created_time'):
                vals['created_time'] = vals.get('create_date')
            else:
                vals['created_time'] = datetime.strptime(vals['created_time'], "%d-%m-%Y %H:%M:%S")
        res = super(HistoryContact, self).create(vals_list)
        return res

    def create_history_contact(self, partner_id, action_id, location=False, description=False, product_id=False):
        try:
            if action_id.code == 'access_web' and product_id:
                action_partner = ' tham khảo sản phẩm ' + product_id.name
            else:
                action_partner = ' tại ' + location
            insert_history = {
                'partner_id': partner_id,
                'action_id': action_id.id,
                'location': location,
                'description': description if description else '',
                'create_date': datetime.now(),
            }
            insert_message = {
                'res_id': partner_id,
                'author_id': 2,
                'message_type': 'notification',
                'model': 'res.partner',
                'is_internal': True,
                'body': action_id.name + action_partner,
            }
            query_insert_history = '''
                INSERT INTO history_contact (partner_id, action_id, location, description, create_date)
                VALUES (
                    %(partner_id)s, %(action_id)s, %(location)s, %(description)s, %(create_date)s
                ) 
            '''
            query_insert_message = '''
                INSERT INTO mail_message (res_id, author_id, message_type, model, is_internal, body)
                VALUES (
                    %(res_id)s,
                    %(author_id)s,
                    %(message_type)s,
                    %(model)s,
                    %(is_internal)s,
                    %(body)s
                )
            '''
            self.env.cr.execute(query_insert_message, insert_message)
            self.env.cr.execute(query_insert_history, insert_history)
            # return self.env.cr.fetchall()
        except Exception as e:
            print(e)
            raise e


class ResPartner(models.Model):
    _inherit = 'res.partner'

    history_ids = fields.One2many('history.contact', 'partner_id', string="History")
    source_name = fields.Char('Source name')
    nick_name = fields.Char('Nick name')
    birthday = fields.Date('Birthday')

    def write(self, vals):
        if vals.get('phone'):
            vals['phone'] = log_ulti.convert_sdt(vals.get('phone'))
        if vals.get('mobile'):
            vals['mobile'] = log_ulti.convert_sdt(vals.get('mobile'))
        return super().write(vals)

    @api.model
    def create(self, vals):
        if vals.get('phone'):
            vals['phone'] = log_ulti.convert_sdt(vals.get('phone'))
        if vals.get('mobile'):
            vals['mobile'] = log_ulti.convert_sdt(vals.get('mobile'))
        return super(ResPartner, self).create(vals)

    def action_open_imint(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': 'https://erp.pontusinc.com/imint',
            'target': 'new',
        }

    def search_imint_avatar(self, url):
        self.ensure_one()
        if url:
            return {
                'type': 'ir.actions.act_url',
                'url': 'https://staging.pontusinc.com/imint/entity-search-url?url_img=%s' %quote(url),
                'target': 'new',
            }

    def action_popup_history_tracking(self):
        self.ensure_one()
        tree_id = self.env.ref('pontusinc_crm.action_partner_history_tree_view').id
        search_view_id = self.env.ref('pontusinc_crm.action_partner_history_search').id
        return {
            'name': _("History action"),
            'type': 'ir.actions.act_window',
            'view_mode': 'tree',
            'views': [(tree_id, 'tree')],
            'res_model': 'history.contact',
            'target': 'new',
            'domain': [('partner_id', '=', self.id)],
            'search_view_id': search_view_id,
            'context': {
                'search_default_group_action': True,
                'search_default_group_create_date': True,
            },
        }

    def action_open_popup_profiling(self):
        self.ensure_one()
        form_id = self.env.ref('pontusinc_crm.popup_profiling_form_view').id
        return {
            'name': _("Search profiling"),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'views': [(form_id, 'form')],
            'res_model': 'search.profiling',
            'target': 'new',
            'context': {
                'default_partner_id': self.id,
                'phone': self.phone,
                'mobile': self.mobile,
                'email': self.email,
                'FBid': self.facebook_id
            },
        }

    def action_open_update_partner(self):
        self.ensure_one()
        view_id = self.env.ref('pontusinc_crm.update_partner_tree_view').id
        return {
            'name': _("Request update info partner"),
            'type': 'ir.actions.act_window',
            'view_mode': 'tree',
            'views': [(view_id, 'tree')],
            'res_model': 'update.partner',
            'target': 'new',
            'domain': [('partner_id', '=', self.id)],
            'context': {
                'default_partner_id': self.id,
            },
        }

    def action_open_shipping(self):
        self.ensure_one()
        view_id = self.env.ref('pontusinc_crm.shipping_tree_view').id
        return {
            'name': _("Shipping"),
            'type': 'ir.actions.act_window',
            'view_mode': 'tree',
            'views': [(view_id, 'tree')],
            'res_model': 'shipping',
            'target': 'new',
            'domain': [('partner_id', '=', self.id)],
        }

    def action_view_traces(self):
        action = self.env["ir.actions.actions"]._for_xml_id("mass_mailing.mailing_trace_action")
        action['name'] = _('Sent Mailings')
        action['views'] = [
            (self.env.ref('mass_mailing.mailing_trace_view_tree_mail').id, 'tree'),
            (self.env.ref('mass_mailing.mailing_trace_view_form').id, 'form')
        ]
        action['domain'] = [('email', 'ilike', self.email)]
        return action

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

    def action_search_profiling(self, key=False, value=False):
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

            template = {
                "q": value,
                "fields": [key],
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
                                'partner_id': self.id
                            })
                            value_log.append({
                                'name': key,
                                'detail': value
                            })
                        # if 'CheckinLocationNames' in dict_data.keys():
                        #     LogUtil.create_log_history_partner(self=self.partner_id, action=self.env.ref(
                        #         'history_contact.action_partner_checkin'), location=dict_data['CheckinLocationNames'])
                    self.write({
                        'search_profiling': value_log
                    })
                    result = self.env['result.profiling'].sudo().create(value_result)
                    return self.action_open_popup_result_profiling(result)
            else:
                return "No further information is available %s: %s" % (key, value)
                # raise ValidationError(
                #     _("No further information is available %s: %s" % (key, value)))

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


class WebsiteVisitor(models.Model):
    _inherit = 'website.visitor'

    # overwrite funtion _upsert_visitor
    def _upsert_visitor(self, access_token, force_track_values=None):
        """ Based on the given `access_token`, either create or return the
        related visitor if exists, through a single raw SQL UPSERT Query.

        It will also create a tracking record if requested, in the same query.

        :param access_token: token to be used to upsert the visitor
        :param force_track_values: an optional dict to create a track at the
            same time.
        :return: a tuple containing the visitor id and the upsert result (either
            `inserted` or `updated).
        """
        create_values = {
            'access_token': access_token,
            'lang_id': request.lang.id,
            # Note that it's possible for the GEOIP database to return a country
            # code which is unknown in Odoo
            'country_code': request.geoip.get('country_code'),
            'website_id': request.website.id,
            'timezone': self._get_visitor_timezone() or None,
            'write_uid': self.env.uid,
            'create_uid': self.env.uid,
            # If the access_token is not a 32 length hexa string, it means that the
            # visitor is linked to a logged in user, in which case its partner_id is
            # used instead as the token.
            'partner_id': None if len(str(access_token)) == 32 else access_token,
        }
        query = """
            INSERT INTO website_visitor (
                partner_id, access_token, last_connection_datetime, visit_count, lang_id,
                website_id, timezone, write_uid, create_uid, write_date, create_date, country_id)
            VALUES (
                %(partner_id)s, %(access_token)s, now() at time zone 'UTC', 1, %(lang_id)s,
                %(website_id)s, %(timezone)s, %(create_uid)s, %(write_uid)s,
                now() at time zone 'UTC', now() at time zone 'UTC', (
                    SELECT id FROM res_country WHERE code = %(country_code)s
                )
            )
            ON CONFLICT (access_token)
            DO UPDATE SET
                last_connection_datetime=excluded.last_connection_datetime,
                visit_count = CASE WHEN website_visitor.last_connection_datetime < NOW() AT TIME ZONE 'UTC' - INTERVAL '8 hours'
                                    THEN website_visitor.visit_count + 1
                                    ELSE website_visitor.visit_count
                                END
            RETURNING id, CASE WHEN create_date = now() at time zone 'UTC' THEN 'inserted' ELSE 'updated' END AS upsert
        """

        if force_track_values:
            create_values['url'] = force_track_values['url']
            create_values['page_id'] = force_track_values.get('page_id')
            query = sql.SQL("""
                WITH visitor AS (
                    {query}, %(url)s AS url, %(page_id)s AS page_id
                ), track AS (
                    INSERT INTO website_track (visitor_id, url, page_id, visit_datetime)
                    SELECT id, url, page_id::integer, now() at time zone 'UTC' FROM visitor
                )
                SELECT id, upsert from visitor;
            """).format(query=sql.SQL(query))
        if create_values.get('partner_id') and create_values.get('url'):
            action = request.env.ref('pontusinc_crm.action_partner_access').sudo()
            self.env['history.contact'].sudo().create_history_contact(create_values.get('partner_id'), action,
                                                                      location=create_values.get('url'))
        self.env.cr.execute(query, create_values)
        return self.env.cr.fetchone()


class WebsiteTrack(models.Model):
    _inherit = 'website.track'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('product_id'):
                visitor = self.env['website.visitor'].sudo().browse(vals.get('visitor_id'))
                if visitor.partner_id:
                    action = request.env.ref('pontusinc_crm.action_partner_access').sudo()
                    product = self.env['product.product'].sudo().browse(vals.get('product_id'))
                    self.env['history.contact'].sudo().create_history_contact(visitor.partner_id.id, action,
                                                                              product_id=product)
        res = super(WebsiteTrack, self).create(vals_list)
        return res


class UpdatePartner(models.Model):
    _name = 'update.partner'
    _description = 'API update information partner'

    partner_id = fields.Many2one('res.partner', string='Partner', required=True, ondelete='cascade')
    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirm'), ('cancel', 'Cancel')], string='State',
                             default="draft")
    name = fields.Char('name')
    phone = fields.Char('phone')
    email = fields.Char('email')
    vat = fields.Char('VAT')
    title = fields.Many2one('res.partner.title', string='Title')
    mobile = fields.Char('Mobile')
    function = fields.Char('Position')

    def action_confirm(self):
        self.ensure_one()
        self.state = 'confirm'
        self.partner_id.write(self.with_context(update_partner=True).read(
            ['name', 'phone', 'email', 'vat', 'title', 'mobile', 'function'])[0])
