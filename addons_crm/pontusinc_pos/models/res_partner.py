from odoo import fields, models, api

class ResPartner(models.Model):
    _inherit = 'res.partner'

    source_id = fields.Many2one('utm.source', string='Source')
    pos_id = fields.Many2one('pos.config', string='Source POS')