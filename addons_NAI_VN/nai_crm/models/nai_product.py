from odoo import fields, models, api, _

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
    partner_latitude = fields.Float(string='Geo Latitude', digits=(10, 7))
    partner_longitude = fields.Float(string='Geo Longitude', digits=(10, 7))
    image_ids = fields.One2many('nai.image.product', 'product_template_id', string='Image')
    type_building = fields.Selection(type_building, string='Type building', default='office_building')
    area = fields.Selection(AREA, string='Area')
    building_parent_id = fields.Many2one('product.template', string='Building parent')
    price_rental = fields.Float("Price rental", compute='calculate_price_rental', store=True, readonly=False)
    acreage = fields.Float('Acreage')
    child_product_ids = fields.One2many('product.template', 'building_parent_id', string='Child product')
    count_building_child = fields.Integer(compute='calculate_count_building_child')
    expense_ids = fields.One2many('nai.expense.product', 'product_id', string='Expense building')

    detailed_type = fields.Selection(
        selection_add=[('expense', 'Expense')],
        ondelete={'expense': 'set service'}  # Chuyển thành 'service' khi bị xóa
    )

    def _detailed_type_mapping(self):
        type_mapping = super()._detailed_type_mapping()
        type_mapping['expense'] = 'service'
        return type_mapping


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



