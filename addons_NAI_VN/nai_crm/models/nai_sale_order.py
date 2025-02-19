from odoo import fields, models, api, _


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
        if self.order_line:
            if len(self.order_line) > 1:
                for rec in self.order_line:
                    if not rec.product_id.building_parent_id:
                        context['default_image'] = rec.product_id.image_1024
            else:
                context['default_image'] = self.order_line[0].product_id.image_1024
        res_id = False
        if self.template_report_ids.filtered(lambda l: l.create_uid.id == self.env.uid):
            res_id = self.template_report_ids.filtered(lambda l: l.create_uid.id == self.env.uid)[-1].id
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


class NaiSaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    price_vn = fields.Float('VND', compute='calculate_price_vn')

    @api.depends('price_unit')
    def calculate_price_vn(self):
        exchange_rate = self.env['ir.config_parameter'].sudo().get_param('nai_crm.exchange_rate', default=25000)
        for record in self:
            if record.price_unit:
                record.price_vn = record.price_unit * exchange_rate
