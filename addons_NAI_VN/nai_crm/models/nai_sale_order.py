from odoo import fields, models, api, _
from odoo import Command

class NAISaleOrder(models.Model):
    _inherit = 'sale.order'

    template_report_ids = fields.One2many('popup.select.fields.report', 'sale_order_id')

    def action_print_so(self):
        self.ensure_one()
        return {
            'name': _("Print Sale Order"),
            'type': 'ir.actions.act_window',
            'views': [(False, 'tree')],
            'res_model': 'popup.select.fields.report',
            'view_mode': 'tree',
            'target': 'new',
        }

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            order_lines = vals.get('order_line', [])
            new_lines = []

            for line in order_lines:
                product_id = line[2].get('product_id') if isinstance(line, (list, tuple)) and len(line) > 2 else None
                if product_id:
                    product = self.env['product.product'].browse(product_id).exists()
                    if product.expense_ids:
                        for expense in product.expense_ids:
                            if expense.self_id:
                                new_line = (0, 0, {
                                    'product_id': expense.self_id.product_variant_id.id,
                                    'product_uom_qty': product.acreage if expense.str_uom == '/m2' else 1,
                                    'price_unit': expense.expense,  # Giá sản phẩm
                                })
                                new_lines.append(new_line)

            # Thêm các dòng sản phẩm expense_ids vào order_line
            vals['order_line'].extend(new_lines)
        res = super(NAISaleOrder, self).create(vals_list)
        return res


class NaiSaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    price_vn = fields.Float('VND', compute='calculate_price_vn')

    @api.depends('price_unit')
    def calculate_price_vn(self):
        exchange_rate = self.env['ir.config_parameter'].sudo().get_param('nai_crm.exchange_rate', default=25000)
        for record in self:
            if record.order_id and record.order_id.state not in ['sale', 'sent']:
                if record.price_unit:
                    record.price_vn = record.price_unit * float(exchange_rate)
                else:
                    record.price_vn = 0

    @api.model_create_multi
    def create(self, vals_list):
        return super().create(vals_list)
