from odoo import models, fields, api

class ResUsers(models.Model):
    _inherit = 'res.users'

    asana_gid = fields.Char('Asana gid')