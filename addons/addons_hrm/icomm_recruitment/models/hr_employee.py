from odoo import fields, models, api

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    certificate = fields.Selection([
        ('graduate', 'Graduate'),
        ('bachelor', 'Bachelor'),
        ('master', 'Master'),
        ('doctor', 'Doctor'),
        ('engineer', 'Engineer'),
        ('other', 'Other'),
    ], 'Certificate Level', default='other', groups="hr.group_hr_user", tracking=True)
    source_id = fields.Many2one('utm.source', string='Source')

class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    source_id = fields.Many2one('utm.source', string='Source')
