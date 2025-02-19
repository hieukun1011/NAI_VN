from odoo import fields, models, _


class NAISaleOrder(models.Model):
    _inherit = 'sale.order'

    template_report_ids = fields.One2many('popup.select.fields.report', 'sale_order_id')

    def action_print_so(self):
        self.ensure_one()
        view_form_id = self.env.ref('nai_crm.popup_select_fields_report_form_view').id
        context = {
            'default_sale_order_id': self.id,
            'create': False
        }
        domain = []
        if self.order_line:
            if len(self.order_line) > 1:
                for rec in self.order_line:
                    if not rec.product_id.building_parent_id:
                        context['default_image'] = rec.product_id.image_1024
            else:
                context['default_image'] = self.order_line[0].product_id.image_1024
        res_id = False
        if self.template_report_ids:
            res_id = self.template_report_ids.filtered(lambda l: l.create_uid == self.env.uid)[-1].id

        return {
            'name': _("Print Sale Order"),
            'type': 'ir.actions.act_window',
            'views': [(view_form_id, 'form')],
            'res_model': 'popup.select.fields.report',
            'view_mode': 'form',
            'res_id': res_id,
            'target': 'new',
            'context': context
        }
