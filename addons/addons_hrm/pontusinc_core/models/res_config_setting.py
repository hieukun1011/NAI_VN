# -*- coding: utf-8 -*-

from odoo import api, fields, models

import logging

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    is_bank = fields.Boolean(string="Is bank", config_parameter='pontusinc_core.is_bank')




    