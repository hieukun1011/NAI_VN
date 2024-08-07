# -*- coding: utf-8 -*-
from datetime import datetime, timedelta

from odoo import models, fields, api

class ResPartner(models.Model):
    _inherit = 'res.partner'

    zalo_user_id = fields.Char('Zalo User Id')

    def send_zalo_message(self, raise_exception=True):
        zalo_configuration = self.env.ref('zalo_configuration.zalo_configuration')
        if zalo_configuration.access_token:
            wizard = self.env['zalo.message.wizard'].create({
                'partner_ids': [(6, 0, self.filtered(lambda x: x.zalo_user_id).ids)],
                'message': ''
            })
            action = self.env.ref('zalo_connector.zalo_message_wizard_action').read([])[0]
            action['res_id'] = wizard.id
            return action




