from odoo import fields, models, api, _
from ..util import api_category_vnpost
import json
import requests
from odoo.exceptions import Warning, UserError

class ShippingPlatform(models.Model):
    _name = 'shipping.platform'
    _description = 'Shipping platform'

    name = fields.Char('Name')
    code = fields.Char('Code')
    image = fields.Binary('Image', readonly=True)
    connected = fields.Boolean('Connected', compute='check_connected', store=False)
    state_id = fields.One2many('shipping.state', 'platform_id', string='State')
    is_partner = fields.Boolean('Is partner')

    def check_connected(self):
        for record in self:
            if record.code == 'vnpost' and self.env.user.token_vnpost:
                record.connected = True
            elif record.code == 'ghn' and self.env.user.token_ghn:
                record.connected = True
            else:
                record.connected = False

    def action_disconnect_shipping_platform(self):
        self.ensure_one()
        if self.connected:
            if self.code == 'vnpost' and self.env.user.token_vnpost:
                self.env.user.token_vnpost = False
                self.connected = False
            elif self.code == 'ghn' and self.env.user.token_ghn:
                self.env.user.token_ghn = False
                self.connected = False

    def action_connect_shipping_platform(self):
        self.ensure_one()
        connected = self.env['shipping.platform.user'].sudo().search([('platform_id', '=', self.id), ('user_id', '=', self.env.user.id)], limit=1)
        view_id = self.env.ref('pontusinc_shipping.shipping_connect_form_view').id
        context = {
            'default_platform_id': self.id,
        }
        if self.code == 'ghn':
            if connected:
                context['default_token'] = connected.token
        elif self.code == 'vnpost':
            if connected:
                context['default_user_login'] = connected.user_login
                context['default_password'] = connected.password
                context['default_customer_code'] = connected.customer_code
        return {
            'name': _("Connect shipping platform"),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'views': [(view_id, 'form')],
            'res_model': 'shipping.platform.user',
            'target': 'new',
            'context': context
        }




class ShippingState(models.Model):
    _name = 'shipping.state'
    _description = 'Shipping state'
    _order = 'sequence, id'

    name = fields.Char('Name')
    sequence = fields.Integer('Sequence')
    code = fields.Char('Code')
    platform_id = fields.Many2one('shipping.platform', string='Shipping platform')


class UserConnectShipping(models.Model):
    _name = 'shipping.platform.user'
    _description = 'User connect shipping platform'

    user_id = fields.Many2one('res.users', required=True, default=lambda self: self.env.user)
    platform_id = fields.Many2one('shipping.platform', string='Shipping platform')
    user_login = fields.Char('Login')
    password = fields.Char('Password')
    token = fields.Char('Token')
    customer_code = fields.Char('Customer code')

    def connect_shipping_platform(self):
        self.ensure_one()
        if self.platform_id.code == 'vnpost':
            url = api_category_vnpost.URL_API_VNPOST + api_category_vnpost.get_token
            headers = {
                "Content-Type": "application/json",
            }
            template = {
                'username': self.user_login,
                'password': self.password,
                'customerCode': self.customer_code,
            }
            session = requests.Session()
            response = session.post(url, data=json.dumps(template), headers=headers)
            if response.status_code == 200:
                data = response.json()
                if data.get('token'):
                    self.platform_id.connected = True
                    self.user_id.sudo().token_vnpost = data.get('token')
                else:
                    raise UserError(_(data.get('errorMessage')))
            else:
                return False
        # elif self.platform_id.code == 'ghn':



