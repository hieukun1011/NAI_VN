from odoo import fields, models, api

class AreaShipping(models.Model):
    _name = 'area.shipping'

    name = fields.Char('Area')
    city_ids = fields.One2many('res.country.state', 'area_id', string='City')
