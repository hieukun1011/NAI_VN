from odoo import fields, models, api, _

class ResPartnerState(models.Model):
    _name = 'res.partner.state'

    name = fields.Char('Name')