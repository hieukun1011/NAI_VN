from odoo import fields, models, api

class ShippingResUsers(models.Model):
    _inherit = 'res.users'

    token_ghn = fields.Char('Token GHN')
    token_vnpost = fields.Char('Token VNPOST')