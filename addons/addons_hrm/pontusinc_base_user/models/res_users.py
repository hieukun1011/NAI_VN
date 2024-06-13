from odoo import fields, models, api

class PontusincResUsers(models.Model):
    _inherit = 'res.users'

    facebook_app_id = fields.Char("Facebook App ID")
    facebook_client_secret = fields.Char("Facebook App Secret")
    department_id = fields.Many2one('hr.department', string='Department', compute='related_department_id', store=True)

    @api.depends('employee_ids')
    def related_department_id(self):
        for record in self:
            if record.employee_ids and record.employee_ids[0].department_id:
                record.department_id = record.employee_ids[0].department_id

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('email'):
                vals['email'] = vals['login']
        return super().create(vals_list)