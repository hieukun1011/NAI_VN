from odoo import fields, models, _

class NaiCRMTeam(models.Model):
    _inherit = 'crm.team'

    product_ids = fields.Many2many('product.template', string='Product')

