from odoo import fields, models, api, _


class ShippingResPartner(models.Model):
    _inherit = 'res.partner'

    def action_open_shipping_waybill(self):
        action = self.env['ir.actions.act_window']._for_xml_id('pontusinc_shipping.act_shipping_waybill_view')
        action["domain"] = [("partner_id", "=", self.id)]
        action["context"] = {
            'default_partner_id': self.id,
            'default_name_receiver': self.name,
            'default_phone_receiver': self.phone if self.phone else self.mobile,
        }
        return action
