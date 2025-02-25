from odoo import fields, models, api, _
from odoo.tools import config
from odoo.exceptions import UserError, ValidationError
type_building = [('office_building', 'Office Building'),
                 ('shopping_mall', 'Shopping Mall'),
                 ('shophouse', 'Shophouse'),
                 ('industrial_parks', 'Industrial Parks'),
                 ('industrial_properties', 'Industrial Properties')]

AREA = [('southern', 'Southern'), ('north', 'North'), ('central_region', 'Central Region')]


class NAIProduct(models.Model):
    _inherit = 'product.template'

    nai_attribute_line_ids = fields.One2many('nai.product.attribute.line', 'product_tmpl_id', 'Buildings Attributes',
                                             copy=True)
    location = fields.Char('Location', copy=True)
    partner_latitude = fields.Float(string='Geo Latitude', digits=(10, 7), compute='geo_localize', store=True)
    partner_longitude = fields.Float(string='Geo Longitude', digits=(10, 7), compute='geo_localize', store=True)
    image_ids = fields.One2many('nai.image.product', 'product_template_id', string='Image')
    type_building = fields.Selection(type_building, string='Type building', default='office_building')
    area = fields.Selection(AREA, string='Area')
    building_parent_id = fields.Many2one('product.template', string='Building parent')
    price_rental = fields.Float("Price rental", compute='calculate_price_rental', store=True, readonly=False)
    acreage = fields.Float('Acreage')
    child_product_ids = fields.One2many('product.template', 'building_parent_id', string='Child product')
    count_building_child = fields.Integer(compute='calculate_count_building_child')
    expense_ids = fields.One2many('nai.expense.product', 'product_id', string='Expense building', copy=True, tracking=True)

    detailed_type = fields.Selection(
        selection_add=[('expense', 'Expense')],
        ondelete={'expense': 'set service'}  # Chuyển thành 'service' khi bị xóa
    )

    @api.model
    def search_fetch(self, domain, field_names, offset=0, limit=None, order=None):
        index = 0
        for rec in domain:
            index += 1
            if rec[0] == 'location':
                geo_obj = self.env['base.geocoder']
                result = geo_obj.geo_find(rec[2])
                if result:
                    domain_test = self._search_by_location(result[0], result[1])
                    # domain[index-1] = self._search_by_location(result[0], result[1])
                    return super().search_fetch(domain_test, field_names, offset, limit, order)
        return super().search_fetch(domain, field_names, offset, limit, order)

    def _detailed_type_mapping(self):
        type_mapping = super()._detailed_type_mapping()
        type_mapping['expense'] = 'service'
        return type_mapping

    @api.depends('location')
    def geo_localize(self):
        for record in self:
            geo_obj = self.env['base.geocoder']
            result = geo_obj.geo_find(record.location)
            if result:
                record.partner_latitude = result[0]
                record.partner_longitude = result[1]
            else:
                record.partner_latitude = False
                record.partner_longitude = False

    @api.model
    def _search_by_location(self, latitude, longitude, radius_km=5):
        """Tìm các record trong bán kính radius_km tính từ (latitude, longitude)"""
        query = """
                SELECT id FROM product_template
                WHERE ( 6371 * acos(
                    cos(radians(%s)) * cos(radians(partner_latitude)) *
                    cos(radians(partner_longitude) - radians(%s)) +
                    sin(radians(%s)) * sin(radians(partner_latitude))
                ) ) <= %s
            """
        self.env.cr.execute(query, (latitude, longitude, latitude, radius_km))
        result_ids = [row[0] for row in self.env.cr.fetchall()]
        return [('id', 'in', result_ids)]



    def calculate_count_building_child(self):
        for record in self:
            record.count_building_child = len(record.child_product_ids)

    @api.depends('list_price', 'acreage')
    def calculate_price_rental(self):
        for record in self:
            if record.list_price and record.acreage and not record.price_rental:
                record.price_rental = record.list_price / record.acreage

    # @api.onchange('price_rental', 'acreage')
    # def calculate_list_price_rental(self):
    #     if self.price_rental and self.acreage:
    #         self.list_price = self.price_rental * self.acreage


class NAIExpenseProduct(models.Model):
    _name = 'nai.expense.product'

    product_id = fields.Many2one('product.template', string='Product')
    name = fields.Char('Name')
    expense = fields.Float('Expense')
    str_uom = fields.Char('Uom')
    currency_id = fields.Many2one(related='product_id.currency_id')
    self_id = fields.Many2one('product.template', string='Self')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('self_id'):
                self_product_id = self.env['product.template'].create([{
                    'name': vals.get('name', 'Default Name'),
                    'detailed_type': 'expense',
                    'list_price': vals.get('expense', 0.0)
                }])
                vals['self_id'] = self_product_id.id if self_product_id else False
        return super().create(vals_list)



