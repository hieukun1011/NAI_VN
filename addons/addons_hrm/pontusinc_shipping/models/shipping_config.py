from odoo import fields, models, api, _

class ShippingConfig(models.Model):
    _name = 'shipping.config'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    company_ids = fields.Many2many('res.company', string='Company')
    according_product_order = fields.Boolean('According to the product in the order', tracking=True)
    is_custom = fields.Boolean('Custom', default=True, tracking=True)
    specific_weight = fields.Float('Specific weight', unit='g', tracking=True)
    length = fields.Float('Length', tracking=True)
    width = fields.Float('Width', tracking=True)
    height = fields.Float('Height', tracking=True)
    sync_automation_state = fields.Boolean('Automation sync state', default=True, tracking=True)
    sync_automation_fee = fields.Boolean('Automation sync fee', default=True, tracking=True)
    late_pick_alert_days = fields.Integer('Late Pick Alert Days', tracking=True)
    late_delivery_alert_days = fields.Integer('Late Delivery Alert Days', tracking=True)