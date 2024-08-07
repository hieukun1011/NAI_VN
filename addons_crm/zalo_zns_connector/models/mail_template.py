# -*- coding: utf-8 -*-

from odoo import fields, models, tools, _
from datetime import date, datetime, timedelta
import requests
import json
from odoo.exceptions import UserError, ValidationError
import logging
_logger = logging.getLogger(__name__)


class MailTemplate(models.Model):
    _inherit = 'mail.template'

    template_id = fields.Char(string="TemplateId")
    create_time = fields.Datetime(string="Thời gian tạo")
    status = fields.Char(string="Trạng thái")
    template_quality = fields.Char(string="Chất lượng")
    price = fields.Float(string="Giá")
    line_ids = fields.One2many('zns.template.line', 'template_id', string="Tham số")

    # đồng bộ danh sách template
    def action_sync_template(self):
        zalo = self.env.ref('zalo_configuration.zalo_configuration')
        access_token = zalo.access_token
        url = "https://business.openapi.zalo.me/template/all?offset=0&limit=100"

        payload={}
        headers = {
            'access_token': access_token
        }

        response = requests.request("GET", url, headers=headers, data=payload)

        if response.status_code == 200:
            datas = json.loads(response.text)
            if datas.get('error') == 0:
                if datas.get('data'):
                    for data in datas.get('data'):
                        if data.get('status') == "ENABLE":
                            template = self.env['mail.template'].search([('template_id','=',str(data.get('templateId')))], limit=1)
                            if not template:
                                temp = self.env['mail.template'].create({
                                    'template_id': str(data.get('templateId')),
                                    'name': data.get('templateName'),
                                    'create_time': datetime.fromtimestamp(float(data.get('createdTime')) / 1e3),
                                    'status': data.get('status'),
                                    'template_quality': data.get('templateQuality'),
                                })
                                # chi tiết template
                                template_detail = requests.request("GET", url="https://business.openapi.zalo.me/template/info?template_id=%s"%(data.get('templateId')), headers={'access_token': access_token}, data={})
                                if template_detail.status_code == 200:
                                    template_detail_datas = json.loads(template_detail.text)
                                    if template_detail_datas.get('error') == 0:
                                        temp.write({
                                            'body_html': "<p>" + str(template_detail_datas.get('data').get('listParams')) + "</p>",
                                            'price': template_detail_datas.get('data').get('price'),
                                        })
            else:
                _logger.warning(datas.get('message'))

class ZNSTemplateLine(models.Model):
    _name = 'zns.template.line'
    _description = 'Config params'

    template_id = fields.Many2one('mail.template', string="Template")
    param_key = fields.Char(string="Key")
    field_id = fields.Many2one('ir.model.fields', string="Value")