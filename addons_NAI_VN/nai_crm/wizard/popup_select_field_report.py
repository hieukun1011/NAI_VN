from odoo import fields, models, api, _

list_proposal_1 = [('name', 'Building name'),
                   ('location', 'Address'),
                   ('landlord', 'Landlord'),
                   ('year_completed', 'Year completed'),
                   ('grade', 'Grade'),
                   ('green_certification', 'Green Certification'),
                   ('nlc', 'NLA'),
                   ('building_structure', 'Building structure'),
                   ('typical_floor', 'Typical floor')]

list_proposal_2 = [('offered_area', 'Offered area'),
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
    list_proposal_1 = fields.Selection(list_proposal_1)
    list_proposal_2 = fields.Selection(list_proposal_2)
    option_1_ids = fields.Many2many(
        'ir.model.fields.selection',
        'popup_select_fields_report_option_1_rel',  # Tên bảng trung gian riêng
        'report_id',  # Tên cột liên kết với model chính
        'selection_id',  # Tên cột liên kết với model Many2many
        domain=[('field_id.model', '=', 'popup.select.fields.report'),
                ('field_id.name', '=', 'list_proposal_1')],
        string="Options"
    )

    option_2_ids = fields.Many2many(
        'ir.model.fields.selection',
        'popup_select_fields_report_option_2_rel',  # Tên bảng trung gian riêng
        'report_id',
        'selection_id',
        domain=[('field_id.model', '=', 'popup.select.fields.report'),
                ('field_id.name', '=', 'list_proposal_2')],
        string="Options"
    )

    option_ids = fields.Many2many(
        'ir.model.fields.selection',
        'popup_select_fields_report_option_rel',  # Tên bảng trung gian riêng
        'report_id',
        'selection_id',
        domain=[('field_id.model', '=', 'popup.select.fields.report'), '|',
                ('field_id.name', '=', 'list_proposal_2'), ('field_id.name', '=', 'list_proposal_1')],
        compute='_get_option_ids'
    )
    show_all = fields.Boolean('Show all')

    @api.depends('show_all')
    def _get_option_ids(self):
        for record in self:
            if record.show_all:
                record.option_1_ids = self.env['ir.model.fields.selection'].search(
                    [('field_id.model', '=', 'popup.select.fields.report'), ('field_id.name', '=', 'list_proposal_1')])
                record.option_2_ids = self.env['ir.model.fields.selection'].search(
                    [('field_id.model', '=', 'popup.select.fields.report'), ('field_id.name', '=', 'list_proposal_2')])
            else:
                if len(record.option_1_ids) == 9 and len(record.option_2_ids) == 10:
                    record.option_1_ids = False
                    record.option_2_ids = False
            record.option_ids = record.option_2_ids + record.option_1_ids



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
                                result[expense.name] = str(expense.expense) + ' ' + str(expense.str_uom)
            else:
                for rec in self.sale_order_id.order_line:
                    if rec.product_id.detailed_type != 'expense':
                        for att in rec.product_id.nai_attribute_line_ids:
                            if att.name == opt.name:
                                result[att.name] = att.value
                        for expense in rec.product_id.expense_ids:
                            if expense.name == opt.name:
                                result[expense.name] = str(expense.expense) + ' ' + str(expense.str_uom)
            if opt.name == 'Building name':
                result_1['Building name'] = self.sale_order_id.order_line[0].product_id.name
            if opt.name == 'Address':
                result_1['Address'] = self.sale_order_id.order_line[0].product_id.location
            if opt.name == 'NLA':
                result_1['NLA'] = self.sale_order_id.order_line[0].product_id.acreage
            if opt.name == 'Asking Rent':
                result_1['Asking Rent'] = self.sale_order_id.order_line[0].price_unit
            if opt.name == 'Note':
                result_1['Note'] = self.sale_order_id.order_line[0].product_id.description
        return result_1, result

    def generate_report(self):
        if not self.sale_order_id:
            self.sale_order_id = self.env.context['active_id']
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


    def detail_template(self):
        self.ensure_one()
        view_form_id = self.env.ref('nai_crm.popup_select_fields_report_form_view').id
        context = {
            'default_sale_order_id': self.sale_order_id.id,
            'create': False
        }
        if self.sale_order_id.order_line:
            if len(self.sale_order_id.order_line) > 1:
                for rec in self.sale_order_id.order_line:
                    if not rec.product_id.building_parent_id:
                        context['default_image'] = rec.product_id.image_1024
            else:
                context['default_image'] = self.sale_order_id.order_line[0].product_id.image_1024

        return {
            'name': _("Print Sale Order"),
            'type': 'ir.actions.act_window',
            'views': [(view_form_id, 'form')],
            'res_model': 'popup.select.fields.report',
            'view_mode': 'form',
            'res_id': self.id,
            'context': context
        }