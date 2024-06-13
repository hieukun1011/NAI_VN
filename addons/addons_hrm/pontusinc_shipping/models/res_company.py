from odoo import fields, models, api

class ShippingResCompany(models.Model):
    _inherit = 'res.company'

    according_product_order = fields.Boolean('According to the product in the order')
    is_custom = fields.Boolean('Custom', default=True)
    specific_weight = fields.Float('Specific weight', unit='g')
    length = fields.Float('Length')
    width = fields.Float('Width')
    height = fields.Float('Height')
    sync_automation_state = fields.Boolean('Automation sync state', default=True)
    sync_automation_fee = fields.Boolean('Automation sync fee', default=True)
    late_pick_alert_days = fields.Integer('Late Pick Alert Days')
    late_delivery_alert_days = fields.Integer('Late Delivery Alert Days')

