from odoo import fields, models, api


class ResBrand(models.Model):
    _name = 'res.brand'
    _description = 'Pontusinc brand management'

    name = fields.Char('Name')
    code = fields.Char('Code')
    company_ids = fields.One2many('res.company', 'brand_id', string='Company')


class ResCompany(models.Model):
    _inherit = 'res.company'

    brand_id = fields.Many2one('res.brand', string='Brand')