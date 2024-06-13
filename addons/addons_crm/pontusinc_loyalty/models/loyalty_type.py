from odoo import fields, models, api

class LoyaltyType(models.Model):
    _name = 'loyalty.type'

    name = fields.Char('Name')