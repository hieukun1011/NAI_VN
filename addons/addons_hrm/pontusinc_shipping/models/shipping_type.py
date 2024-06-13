from odoo import fields, models, api

class ShippingType(models.Model):
    _name = 'shipping.type'

    scope = fields.Selection([('domestic', 'Domestic'), ('foreign', 'Foreign')], string='Scope', default="domestic")
    code = fields.Char('Code')
    name = fields.Char('Name')
    category = fields.Char('Category')
    platform_id = fields.Many2one('shipping.platform', string='Platform')

class ShippingCategoryService(models.Model):
    _name = 'shipping.category.service'

    shipping_type_id = fields.Many2one('shipping.type')
    name = fields.Char('Name')
    code = fields.Char('Code')
    category = fields.Char('Category')

class ShippingServiceProperties(models.Model):
    _name = 'shipping.service.properties'

    service_id = fields.Many2one('shipping.category.service')
    name = fields.Char('Name')
    code = fields.Char('Name')