from odoo import fields, models


class NaiResConfigSetting(models.TransientModel):
    _inherit = 'res.config.settings'

    exchange_rate = fields.Float('Foreign exchange rate', config_parameter='nai_crm.exchange_rate')
