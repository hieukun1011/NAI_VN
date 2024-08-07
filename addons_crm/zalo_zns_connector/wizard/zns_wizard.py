# -*- coding: utf-8 -*-
from odoo import models, fields, api, tools, _
from odoo.exceptions import ValidationError, UserError
from datetime import date, datetime, timedelta
import requests
import json
import re
import base64


class ZNSWizard(models.TransientModel):
    _name = 'zns.wizard'
    _description = 'ZNS Message'

    template_id = fields.Many2one('mail.template', 'Template', required=True)
    model = fields.Char('Model')

    @api.model
    def default_get(self, default_fields):
        vals = super(ZNSWizard, self).default_get(default_fields)
        if 'model' in default_fields and 'model' not in vals:
            vals['model'] = self.env.context.get('active_model')
        # if 'template_id' in default_fields and 'template_id' not in vals and vals.get('model'):
        #     vals['template_id'] = self.env['mail.template'].search(
        #         [('model', '=', vals['model']), ('template_id', '!=', False)], limit=1, order='name').id
        return vals
    
    def send_zns_wizard(self):

        obj = self.sudo().env[self.sudo().template_id.model_id.model].browse(self.env.context.get('active_id'))
        if not obj.partner_id.phone:
            raise ValidationError(_("Khách hàng chưa có thông tin Số điện thoại!"))
        phone = obj.partner_id.phone
        phone = str(phone).replace(' ', '')
        if str(phone[0]) == "0":
            phone = str(phone).replace("0", "84", 1)
        if str(phone[0]) == "+":
            phone = str(phone).replace("+", "")
        zalo = self.env.ref('zalo_configuration.zalo_configuration')
        access_token = zalo.access_token
        if not self.template_id.line_ids:
            raise ValidationError(_("Hãy thiết lập Tham số cho Template trước!"))
        
        url = "https://business.openapi.zalo.me/message/template"
        payload = json.dumps({
            "phone": phone,
            "template_id": self.template_id.template_id,
            "template_data": self.get_params(obj),
            "tracking_id": self.sudo().template_id.model_id.model + "_" + str(obj.id),
            'appsecret_proof': zalo.generate_appsecret_proof(),
        })
        headers = {
            'access_token': access_token,
            'Content-Type': 'application/json'
        }

        response = requests.request("POST", url, headers=headers, data=payload)
        if response.status_code == 200:
            datas = json.loads(response.text)
            if datas.get('error') != 0:
                raise ValidationError(_("Lỗi %s: %s"%(datas.get('error'), datas.get('message'))))
            else:
                self.env['mail.mail'].sudo().create({
                    'template_id': self.template_id.id,
                    'subject': datas.get('data').get('msg_id'),
                    'date': tools.datetime.now(),
                    'state': 'outgoing',
                })

    # lấy giá trị theo trường mapping
    def get_params(self, obj):
        data = {}
        for line in self.template_id.line_ids:
            field_value = ''
            try:
                if line.field_id.name in obj._fields and obj._fields.get(line.field_id.name).type == 'selection':
                    value = obj.mapped(line.field_id.name) and obj.mapped(line.field_id.name)[0] or ''
                    field_value = dict(obj.fields_get(allfields=[line.field_id.name])[line.field_id.name]['selection'])[value]
                elif line.field_id.name in obj._fields and obj._fields.get(line.field_id.name).type != 'selection':
                    if obj._fields.get(line.field_id.name).type in ['date','datetime']:
                        field_value = (obj.mapped(line.field_id.name)[0] + timedelta(hours=7)).strftime("%d/%m/%Y")
                    elif obj._fields.get(line.field_id.name).type == 'many2one':
                        field_value = str(obj.mapped(line.field_id.name+'.name') and obj.mapped(line.field_id.name+'.name')[0] or '')
                    elif obj._fields.get(line.field_id.name).type == 'html':
                        text_cmp = re.compile('<.*?>')
                        field_value = re.sub(text_cmp, '', str(obj.mapped(line.field_id.name) and obj.mapped(line.field_id.name)[0] or ''))
                    else:
                        field_value = str(obj.mapped(line.field_id.name) and obj.mapped(line.field_id.name)[0] or '')
            except:
                field_value = str(obj.mapped(line.field_id.name)[0] or '')
            if not field_value:
                field_value = "Null"
            data[line.param_key] = field_value
        return data