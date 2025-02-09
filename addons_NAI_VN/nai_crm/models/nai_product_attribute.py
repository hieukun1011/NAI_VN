from odoo import fields, models, api


class NAIProductAttribute(models.Model):
    _name = 'nai.product.attribute'

    name = fields.Char('Name')


class NAIAttributeProductLine(models.Model):
    _name = 'nai.product.attribute.line'

    product_tmpl_id = fields.Many2one('product.template', string='Product')
    name = fields.Char(string="Value", related="attribute_id.name")
    value = fields.Char('Value')
    attribute_id = fields.Many2one(
        comodel_name='nai.product.attribute',
        required=True, ondelete='cascade', index=True)

class NAIImageProduct(models.Model):
    _name = 'nai.image.product'


