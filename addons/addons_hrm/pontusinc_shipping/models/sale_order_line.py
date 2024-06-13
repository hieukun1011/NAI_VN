from odoo import fields, models

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    shipping_id = fields.Many2one('shipping.waybill', string="Shipping waybill")