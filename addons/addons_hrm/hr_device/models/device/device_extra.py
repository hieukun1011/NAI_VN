# -*- coding: utf-8 -*- 
from odoo import models, fields, api, _, tools
from odoo.exceptions import ValidationError
from odoo.modules.module import get_module_resource
import base64

import logging

_logger = logging.getLogger(__name__)


class ExtraDevice(models.Model):
    _name = 'hr.device.extra'
    _inherit = ['hr.device', 'image.mixin']
    _description = 'Device Type'

    @api.model
    def _default_image(self):
        image_path = get_module_resource('hr_device', 'static/img', 'default_image.png')
        return base64.b64encode(open(image_path, 'rb').read())

    code = fields.Char('Mã thiết bị', size=50, required=True)
    name = fields.Char('Tên vật tư', size=255, required=True)
    main_device_id = fields.Many2one('hr.device.main', string='Thiết bị chính')
    amount = fields.Integer('Số lượng', size=5, default=1)
    price = fields.Integer('Giá')
    partner = fields.Char('Nhà cung cấp')
    description_images_ids = fields.One2many('hr.device.image', 'extra_device_id', string='Hình ảnh mô tả')
    parts_in_device_ids = fields.One2many('hr.device.parts.in', 'extra_device_id', 'Linh kiện/Vật tư')
    count_parts_in_device = fields.Integer('Quantity Parts In Devices', compute="_compute_quantity_of_parts_in_device")
    image_1920 = fields.Image(default=_default_image)

    _sql_constraints = [('unique_code', 'unique(code)', 'Mã đã tồn tại!!.')]

    @api.onchange('code')
    def change_code(self):
        for record in self:
            if record.code:
                code = record.code
                record.code = code.upper()

    @api.constrains('amount')
    def check_amount(self):
        for record in self:
            if record.amount <= 0:
                raise ValidationError(_('Quantity must be greater than 0'))

    @api.depends('parts_in_device_ids')
    def _compute_quantity_of_parts_in_device(self):
        for record in self:
            record.count_parts_in_device = len(record.parts_in_device_ids)

    def get_parts_in_device_in_main_device(self):
        action = self.env.ref('hr_device.act_device_parts_in_view').read()[0]
        if self:
            action['display_name'] = self.display_name
            action['context'] = {'search_default_extra_device_id': self.id}
        return action

    def open_liquidate(self):
        self.activate = 'liquidate'

    def open_less_use(self):
        self.activate = 'less_use'

    def open_loss(self):
        self.activate = 'loss'
