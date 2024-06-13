# -*- coding: utf-8 -*-
import base64

from odoo import models, fields, api, _, tools
from odoo.modules import get_module_resource


class Device(models.Model):
    _name = 'hr.device'
    _description = "Device"

    date_import = fields.Date('Ngày nhập', required=True, default=fields.Date.today(),tracking=True)
    first_date_use = fields.Date('Ngày tính khấu hao', default=fields.Date.today())
    period = fields.Integer(string='Bảo hành(Tháng)')
    description = fields.Html('Mô tả', size=1500)
    activate = fields.Selection(
        [('not_used', 'Chưa sử dụng'), ('usage', 'Đang sử dụng'), ('out_of_warranty', 'Hết bảo hành'),
         ('liquidate', 'Chờ thanh lý'), ('less_use', 'Đang Hỏng'), ('loss', 'Đã bị Mất')],
        'Trạng thái', required=True, default='not_used', tracking=True)

class DeviceImages(models.Model):
    _name = 'hr.device.image'
    _description = 'Device Image'

    name = fields.Char('Name', size=100, required=True)
    image = fields.Binary('Image')
    extra_device_id = fields.Many2one('hr.device.main')
    main_device_id = fields.Many2one('hr.device.main')
    parts_device_id = fields.Many2one('hr.device.parts.in')
    description = fields.Text('Description', size=600)

    @api.model
    def create(self, vals):
        print(vals)
        res = super(DeviceImages, self).create(vals)
        return res

class DeviceGroup(models.Model):
    _name = 'device.group'

    name = fields.Char(string='Device Group Name')
    group_ids = fields.Char(string='ID Device Group')
    description = fields.Text('Description')

    @api.model
    def create(self, vals):
        vals['group_ids'] = self.env['ir.sequence'].next_by_code('device.group')
        return super(DeviceGroup, self).create(vals)