from odoo import fields, models

class HrDepartment(models.Model):
    _inherit = 'hr.department'

    deputy_id = fields.Many2one('hr.employee', string='Deputy department')
