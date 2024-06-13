from odoo import fields, models, api

class Nation(models.Model):
    _name = 'nation'
    _description = 'Nation'


    code = fields.Char(string='code')
    name = fields.Char(string='Name')

