from odoo import fields, models, api


class ShippingStockPicking(models.Model):
    _inherit = 'stock.picking'

    waybill_id = fields.Many2one('shipping.waybill', string='Waybill')

    def button_validate(self):
        res = super(ShippingStockPicking, self).button_validate()
        for record in self:
            if record.waybill_id and record.waybill_id.code_shipping:
                record.waybill_id.post_order_by_draft()
        return res

    def action_cancel(self):
        res = super(ShippingStockPicking, self).action_cancel()
        for record in self:
            if record.waybill_id and record.waybill_id.code_shipping:
                record.waybill_id.action_cancel_waybill()
        return res
