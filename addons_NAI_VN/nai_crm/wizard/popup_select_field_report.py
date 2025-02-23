from odoo import fields, models, api

list_proposal = [('all', 'ALL'),
                 ('name', 'Building name'),
                 ('location', 'Address'),
                 ('landlord', 'Landlord'),
                 ('year_completed', 'Year completed'),
                 ('grade', 'Grade'),
                 ('green_certification', 'Green Certification'),
                 ('nlc', 'NLA'),
                 ('building_structure', 'Building structure'),
                 ('typical_floor', 'Typical floor'),
                 ('offered_area', 'Offered area'),
                 ('availability', 'Availability'),
                 ('asking_rent', 'Asking Rent'),
                 ('service_charge', 'Service charge'),
                 ('parking_area', 'Parking area'),
                 ('ac_system', 'AC system'),
                 ('elevator', 'Elevator'),
                 ('ceiling_height', 'Ceiling height'),
                 ('other', 'Other'),
                 ('note', 'Note')]

proposal = ['Building name',
            'Location',
            'Landlord',
            'Year completed',
            'Grade',
            'Green Certification',
            'NLA',
            'Building structure',
            'Typical floor',
            'Offered area',
            'Availability',
            'Asking Rent',
            'Service charge',
            'Parking area',
            'AC system',
            'Elevator',
            'Ceiling height',
            'Other',
            'Note']

class PopupSelectFields(models.Model):
    _name = 'popup.select.fields.report'

    name = fields.Char('Name')
    sale_order_id = fields.Many2one('sale.order')
    fields_ids = fields.Many2many('ir.model.fields')
    image = fields.Image("Variant Image", max_width=1024, max_height=250)
    list_proposal = fields.Selection(list_proposal)
    option_ids = fields.Many2many('ir.model.fields.selection',
                                  domain=[('field_id.model', '=', 'popup.select.fields.report'),
                                          ('field_id.name', '=', 'list_proposal')],
                                  string="Options")

    def get_sale_order_values(self):
        """Lấy dữ liệu từ sale.order dựa vào fields_ids được chọn"""
        result_1 = {
            'type': self.sale_order_id.order_line[0].product_id.type_building,
            'area': self.sale_order_id.order_line[0].product_id.area,
        }
        result = {}
        for opt in self.option_ids:
            if opt.name == 'ALL':
                for rec in self.sale_order_id.order_line:
                    if rec.product_id.detailed_type != 'expense':
                        result['location'] = rec.product_id.location
                        for att in rec.product_id.nai_attribute_line_ids:
                            if att.name in proposal:
                                result[att.name] = att.value
                        for expense in rec.product_id.expense_ids:
                            if expense.name in proposal:
                                result[expense.name] = expense.expense + ' ' + expense.str_uom
            else:
                for rec in self.sale_order_id.order_line:
                    if rec.product_id.detailed_type != 'expense':
                        for att in rec.product_id.nai_attribute_line_ids:
                            if att.name == opt.name:
                                result[att.name] = att.value
                        for expense in rec.product_id.expense_ids:
                            if expense.name == opt.name:
                                result[expense.name] = str(expense.expense) + ' ' + expense.str_uom
            if opt.name == 'Building name':
                result_1['Building name'] = self.sale_order_id.order_line[0].product_id.name
            if opt.name == 'Address':
                result_1['Address'] = self.sale_order_id.order_line[0].product_id.location
            if opt.name == 'NLA':
                result_1['NLA'] = self.sale_order_id.order_line[0].product_id.acreage
            if opt.name == 'Asking Rent':
                result_1['Asking Rent'] = self.sale_order_id.order_line[0].price_unit
            if opt.name == 'Note':
                result_1['Note'] = self.sale_order_id.order_line[0].product_id.note
        return result_1, result

    def generate_report(self):
        data = {}

        if self.sale_order_id:
            company = self.sale_order_id.company_id
            logo = company.logo  # Lấy logo

            # 🛠 Kiểm tra kiểu dữ liệu logo để tránh lỗi decode
            if logo and isinstance(logo, bytes):
                logo = logo.decode('utf-8')

            data = {
                'name_abc': '123123'
            }

            attr_product = {}
            for rec in self.sale_order_id.order_line.mapped('product_id.nai_attribute_line_ids'):
                attr_product[rec.name] = rec.value
            data['attr_product'] = attr_product

        for rec in self.fields_ids:
            field_value = getattr(self.sale_order_id, rec.name, False)
            if rec.ttype not in ['many2one', 'many2many', 'one2many']:
                data[rec.name] = field_value
            elif field_value:
                data[rec.name] = field_value.name if rec.ttype == 'many2one' else field_value.mapped('name')

        return self.env.ref('nai_crm.action_custom_quotation_report').report_action(self)



