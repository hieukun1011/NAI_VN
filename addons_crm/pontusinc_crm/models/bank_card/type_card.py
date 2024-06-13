from odoo import fields, models, api, _

class CardType(models.Model):
    _name = 'card.type'

    name = fields.Char('Name')