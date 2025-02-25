from odoo import fields, models, api, _
from odoo.exceptions import UserError

class NaiResPartner(models.Model):
    _inherit = 'res.partner'

    @api.constrains('phone')
    def constrains_phone_partner(self):
        for record in self:
            if record.phone:
                len_partner = self.sudo().search_count([
                    ('phone', 'ilike', record.phone),
                    ('phone', '!=', False),
                ])
                if len_partner > 1:
                    raise UserError(_(f'''Phone number {record.phone} already exists in the system'''))
