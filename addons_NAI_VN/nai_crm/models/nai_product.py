from odoo import fields, models, api, _


class NAIProduct(models.Model):
    _inherit = 'product.template'

    nai_attribute_line_ids = fields.One2many('nai.product.attribute.line', 'product_tmpl_id', 'Buildings Attributes',
                                             copy=True)
    location = fields.Char('Location', copy=True)
    partner_latitude = fields.Float(string='Geo Latitude', digits=(10, 7))
    partner_longitude = fields.Float(string='Geo Longitude', digits=(10, 7))
    image_ids = fields.One2many('nai.image.product', 'product_template_id', string='Image')
