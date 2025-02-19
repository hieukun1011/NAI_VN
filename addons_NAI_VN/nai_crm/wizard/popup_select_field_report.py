from odoo import fields, models, api

class PopupSelectFields(models.Model):
    _name = 'popup.select.fields.report'

    name = fields.Char('Name')
    sale_order_id = fields.Many2one('sale.order')
    fields_ids = fields.Many2many('ir.model.fields')
    image = fields.Image("Variant Image", max_width=1024, max_height=1024)

    def get_sale_order_values(self, sale_order_id):
        """Lấy dữ liệu từ sale.order dựa vào fields_ids được chọn"""
        result = {}
        for rec in self.sale_order_id.order_line:
            for att in rec.product_id.nai_attribute_line_ids:
                result[att.name] = att.value
        for rec in self.fields_ids:
            field_value = getattr(self.sale_order_id, rec.name, False)
            if rec.ttype not in ['many2one', 'many2many', 'one2many']:
                result[rec.field_description] = field_value
            elif field_value:
                result[rec.field_description] = field_value.display_name if rec.ttype == 'many2one' else field_value.mapped('display_name')
        return result

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



