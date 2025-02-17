from odoo import fields, models, api, _

type_building = [('office_building', 'Office Building')]
AREA = [('southern', 'Southern'), ('north', 'North'), ('central_region', 'Central Region')]


class NAIProduct(models.Model):
    _inherit = 'product.template'

    nai_attribute_line_ids = fields.One2many('nai.product.attribute.line', 'product_tmpl_id', 'Buildings Attributes',
                                             copy=True)
    location = fields.Char('Location', copy=True)
    partner_latitude = fields.Float(string='Geo Latitude', digits=(10, 7))
    partner_longitude = fields.Float(string='Geo Longitude', digits=(10, 7))
    image_ids = fields.One2many('nai.image.product', 'product_template_id', string='Image')
    type_building = fields.Selection(type_building, string='Type building', default='office_building')
    area = fields.Selection(AREA, string='Area')
    building_parent_id = fields.Many2one('product.template', string='Building parent')
