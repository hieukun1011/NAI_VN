from odoo import fields, models, api, _

class ShippingResConfigSetting(models.Model):
    _inherit = 'res.config.settings'

    according_product_order = fields.Boolean('According to the product in the order')
    is_custom = fields.Boolean('Custom')
    specific_weight = fields.Float('Specific weight')
    length = fields.Float('Length')
    width = fields.Float('Width')
    height = fields.Float('Height')
    sync_automation_state = fields.Boolean('Automation sync state')
    sync_automation_fee = fields.Boolean('Automation sync fee')
