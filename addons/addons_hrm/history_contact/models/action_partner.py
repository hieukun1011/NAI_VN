from odoo import fields, models, api

class ActionPartner(models.Model):
    _name = 'action.partner'
    _description = 'Action partner'

    code = fields.Char('Code')
    name = fields.Char('Action', required=True)