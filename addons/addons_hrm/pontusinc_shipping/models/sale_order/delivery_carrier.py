from odoo import fields, models, api


class ShippingDeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    shipping_fee_ids = fields.One2many('shipping.fee', 'shipping_method_id', string='Shipping fee')
    area_shipping_ids = fields.Many2many('area.shipping', string='Area shipping')
    city_ids = fields.Many2many('res.country.state', string='City')
    district_ids = fields.Many2many('res.country.district', string='District')
    ward_ids = fields.Many2many('res.country.ward', string='Ward')

    @api.onchange('area_shipping_ids', 'city_ids', 'district_ids')
    def check_undeliverable_area(self):
        self.ensure_one()
        if self.area_shipping_ids or self.city_ids or self.district_ids:
            if not self.area_shipping_ids or (
                    self.area_shipping_ids and self.city_ids and self.city_ids.area_id.id not in self.area_shipping_ids.ids):
                self.city_ids = False
                self.district_ids = False
                self.ward_ids = False
            elif not self.city_ids or (
                    self.city_ids and self.district_ids and self.district_ids.state_id.id not in self.city_ids.ids):
                self.district_ids = False
                self.ward_ids = False
            elif not self.district_ids or (self.ward_ids and self.ward_ids.district_id.id not in self.district_ids.ids):
                self.ward_ids = False
