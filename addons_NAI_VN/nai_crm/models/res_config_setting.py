from odoo import fields, models


class NaiResConfigSetting(models.TransientModel):
    _inherit = 'res.config.settings'

    exchange_rate = fields.Float('Foreign exchange rate', config_parameter='nai_crm.exchange_rate')

    def set_values(self):
        super(NaiResConfigSetting, self).set_values()
        new_exchange_rate = self.exchange_rate
        self.env['sale.order.line']._update_exchange_rate(new_exchange_rate)