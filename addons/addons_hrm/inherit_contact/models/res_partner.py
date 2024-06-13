from odoo import fields, models

class ResPartner(models.Model):
    _inherit = 'res.partner'

    search_profiling = fields.Char('Search profiling', tracking=True)