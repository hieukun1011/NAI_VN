from odoo import fields, models, api, _


class HrShift(models.Model):
    _name = 'hr.shift'
    _description = 'Config employee shift'

    employee_id = fields.Many2one('hr.employee', string='Employee')
