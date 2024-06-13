# -*- coding: utf-8 -*-

from odoo import api, fields, models

import logging

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    have_orders = fields.Boolean(related='company_id.have_orders',  readonly=False)
    auto_activate_card = fields.Boolean(related='company_id.auto_activate_card',  readonly=False)
    proviso = fields.Selection(related='company_id.proviso',  readonly=False)
    minimum_quantity = fields.Integer(related='company_id.minimum_quantity',  readonly=False)
    type_minimum_quantity = fields.Selection(related='company_id.type_minimum_quantity',  readonly=False)
    minimum_spending = fields.Float(related='company_id.minimum_spending',  readonly=False)
    score_deadline = fields.Float(related='company_id.score_deadline',  readonly=False)
    option_score_deadline = fields.Selection(related='company_id.option_score_deadline',  readonly=False)

    def action_company_create_new(self):
        return {
            'view_mode': 'form',
            'res_model': 'res.company',
            'type': 'ir.actions.act_window',
            'target': 'new',
        }



    