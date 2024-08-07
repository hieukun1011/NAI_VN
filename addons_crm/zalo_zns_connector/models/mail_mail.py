# -*- coding: utf-8 -*-

from odoo import fields, models, tools, _
from datetime import date, datetime, timedelta
import requests
import json
from odoo.exceptions import UserError, ValidationError
import logging
_logger = logging.getLogger(__name__)


class MailMail(models.Model):
    _inherit = 'mail.mail'

    template_id = fields.Many2one('mail.template', string="Template")
    zns_partner_id = fields.Many2one('res.partner', string="Contact")

    def action_sync_status(self):
        zalo = self.env.ref('zalo_configuration.zalo_configuration')
        access_token = zalo.access_token
        mail_data = self.search([('date', '>=', datetime.now() - timedelta(days=10)), ('state', 'in', ['outgoing','sent','exception']), ('template_id', '!=', False)])
        if mail_data:
            for mail in mail_data:
                response = requests.request("GET", url="https://business.openapi.zalo.me/message/status?message_id=%s"%(mail.subject), headers={'access_token': access_token}, data={})

                if response.status_code == 200:
                    datas = json.loads(response.text)
                    if datas.get('error') == 0:
                        state = 'outgoing'
                        if datas.get('data').get('status') == -1:
                            state = 'cancel'
                        elif datas.get('data').get('status') == 0:
                            state = 'sent'
                        elif datas.get('data').get('status') == 1:
                            state = 'received'
                        mail.write({
                            'state': state,
                            'headers': datas.get('data').get('message'),
                        })
                    else:
                        _logger.warning(datas.get('message'))