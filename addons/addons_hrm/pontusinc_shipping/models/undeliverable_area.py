from odoo import fields, models, api, _

class UndeliverableArea(models.Model):
    _name = 'undeliverable.area'
    _description = 'Config undeliverable area'

    platform_id = fields.Many2one('shipping.platform', string='Shipping platform')
    city_id = fields.Many2one('res.country.state', string='City')
    district_id = fields.Many2one('res.country.district', string='District')
    ward_id = fields.Many2one('res.country.ward', string='Ward')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)