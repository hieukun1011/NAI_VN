from odoo import fields, models, _


class NAISaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_print_so(self):
        self.ensure_one()
        view_id = self.env.ref('nai_crm.popup_select_fields_report_form_view').id
        context = {
            'default_sale_order_id': self.id,
        }
        return {
            'name': _("Print Sale Order"),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'views': [(view_id, 'form')],
            'res_model': 'popup.select.fields.report',
            'target': 'new',
            'context': context
        }
