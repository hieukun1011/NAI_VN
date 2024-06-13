from odoo import fields, models, api

class CategoryDevice(models.Model):
    _name = 'category.device'

    name = fields.Char('Name')
    area_id = fields.One2many('category.device.area', 'category_id', string='Category area')

class CategoryDeviceArea(models.Model):
    _name = 'category.device.area'

    name = fields.Char('Name')
    category_id = fields.Many2one('category.device', string='Category')