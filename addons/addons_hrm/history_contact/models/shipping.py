from odoo import fields, models, api, _

class StateShipping(models.Model):
    _name = 'state.shipping'
    _order = 'sequence, id'
    _description = 'State Shipping'

    name = fields.Char('Name')
    sequence = fields.Integer('Sequence')

class ShippingUnit(models.Model):
    _name = 'shipping.unit'
    _description = 'Shipping Unit'

    name = fields.Char('Name')
    code = fields.Char('Code')

class Shipping(models.Model):
    _name = 'shipping'
    _description = 'Shipping'

    partner_id = fields.Many2one('res.partner', string='Partner')
    sale_order_id = fields.Many2one('sale.order', string='Sale order', domain="[('partner_id', '=', partner_id)]")
    product_ids = fields.Many2many('product.product', string='Product')
    state_id = fields.Many2one('state.shipping', string='State')
    shipping_unit_id = fields.Many2one('shipping.unit', string='Shipping unit')
    total_price = fields.Float('Price', compute="get_total_amount_sale_order")
    company_id = fields.Many2one('res.company', string='Company', related='sale_order_id.company_id')
    platform = fields.Char('Platform')


    @api.depends('sale_order_id')
    def get_total_amount_sale_order(self):
        for record in self:
            if record.sale_order_id:
                record.total_price = record.sale_order_id.amount_total


    @api.onchange('sale_order_id')
    def get_product_by_sale_order(self):
        product = []
        if self.sale_order_id:
            if self.sale_order_id.order_line:
                for rec in self.sale_order_id.order_line:
                    product.append(rec.product_id.id)
            elif self.sale_order_id.website_order_line:
                for ret in self.sale_order_id.website_order_line:
                    product.append(ret.product_id.id)
            self.product_ids = [(6, 0, product)]
