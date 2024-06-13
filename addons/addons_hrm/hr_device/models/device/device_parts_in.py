# -*- coding: utf-8 -*- 
from odoo import models, fields, api, _, tools
from odoo.exceptions import ValidationError
import logging
from odoo.modules.module import get_module_resource
import base64

_logger = logging.getLogger(__name__)


class PartsInDevice(models.Model):
    _name = 'hr.device.parts.in'
    _inherit = ['hr.device', 'image.mixin']
    _description = 'Parts In Device'

    @api.model
    def _default_image(self):
        image_path = get_module_resource('hr_device', 'static/img', 'default_image.png')
        return base64.b64encode(open(image_path, 'rb').read())

    code = fields.Char('Mã thiết bị', size=50, required=True)
    name = fields.Char('Tên vật tư', size=255, required=True)
    main_device_id = fields.Many2one('hr.device.main', 'Thiết bị chính')
    extra_device_id = fields.Many2one('hr.device.extra', 'Thiết bị phụ tùng', required=True,
                                      domain="[('main_device_id', '=', main_device_id)]")
    amount = fields.Integer('Số lượng', size=5, default=1)
    price = fields.Integer('Giá')
    partner = fields.Char('Nhà cung cấp')

    location = fields.Text('Vị trí', tracking=True)
    description_images_ids = fields.One2many('hr.device.image', 'parts_device_id', string='Hình ảnh mô tả')
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
        for item in self:
            if item.amount < 0:
                raise ValidationError(_('Quantity must be greater than 0'))

    def open_liquidate(self):
        self.activate = 'liquidate'

    def open_less_use(self):
        self.activate = 'less_use'

    def open_loss(self):
        self.activate = 'loss'
