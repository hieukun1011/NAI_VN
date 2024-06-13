from odoo import fields, models, api, _


class ShippingFee(models.Model):
    _name = 'shipping.fee'
    _description = 'Shipping fee'

    name = fields.Char('Name')
    type_fee = fields.Selection(
        [('value', 'Value'), ('weight', 'Weight')],
        'Type fee', required=True, default='value')
    type_shipping = fields.Selection(
        [('via_partners', 'Via partners'), ('self_shipment', 'Self-shipment'),
         ('external_shipping', 'External shipping'), ('customer_pickup', 'Customer pickup')],
        'Type fee', required=True, default='via_partners')
    value_min = fields.Float('Value min')
    value_max = fields.Float('Value max')
    weight_min = fields.Float('Weight min')
    weight_max = fields.Float('Weight max')
    shipping_platform_id = fields.Many2many('shipping.platform', string='Shipping platform')
    shipping_fee = fields.Float('Shipping fee')
    shipping_method_id = fields.Many2one('delivery.carrier')
