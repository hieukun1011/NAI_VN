from odoo import fields, models, api


class View(models.Model):
    _inherit = 'ir.ui.view'

    # def _get_inheriting_views(self):
    #     result = super()._get_inheriting_views()
    #     if len(self) == 1 and self.model == 'res.partner' and self.xml_id == 'base.view_partner_form':
    #         is_bank = self.env['ir.config_parameter'].sudo().get_param('pontusinc_core.is_bank')
    #         if not is_bank:
    #             result -= self.env.ref('pontusinc_crm.view_customer_360_form')
    #         # else:
    #         #     result += self.env.ref('pontusinc_crm.view_customer_360_form')
    #     return result
