from odoo import fields, models, api

class ArriveLate(models.Model):
    _inherit = 'arrive.late'

    is_self = fields.Boolean('Is self', compute='_check_access_write', default=False)

    def _check_access_write(self):
        for record in self:
            if record.employee_id.user_id == self.env.user:
                record.is_self = True
            else:
                record.is_self = False