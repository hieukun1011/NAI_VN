from odoo import fields, models, api

class PopupSelectFields(models.TransientModel):
    _name = 'popup.select.fields.report'


    sale_order_id = fields.Many2one('sale.order')
    fields_ids = fields.Many2many('ir.model.fields')

    def generate_report(self):
        selected_fields = []
        for rec in self.fields_ids:
            selected_fields.append(rec.name)
        # Gọi phương thức tạo báo cáo với các trường đã chọn
        return self.env.ref('nai_crm.action_custom_quotation_report').report_action(self.sale_order_id, data={
            'company_id': self.sale_order_id.company_id})