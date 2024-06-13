# -*-coding: utf-8 -*-


from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import re
import logging
from datetime import datetime, timedelta
from odoo.exceptions import Warning, UserError

_logger = logging.getLogger(__name__)


class EmsEquipmentExport(models.Model):
    _name = 'ems.equipment.export'
    _inherit = 'mail.thread'
    _description = 'Equipments Export'

    @api.model
    def _default_code(self):
        last_id = self.search([], order='id desc', limit=1).id
        _logger.warning(last_id)
        last_id += 1
        code = 'EX' + str(last_id).zfill(5)
        return code

    @api.model
    def _default_user(self):
        return self.env.context.get('user_id', self.env.user.id)

    code = fields.Char('Số phiếu', size=30, required=True,
                       tracking=True, default=lambda self: self._default_code())
    type = fields.Selection([('import', 'Nhận bàn giao'), ('export', 'Xuất bàn giao')], string='Loại bàn giao',
                            default="export", required=True)
    export_date = fields.Date('Ngày bàn giao', required=True, tracking=True, default=fields.Date.today())

    category_id = fields.Many2one('hr.maintenance.equipment.category', 'Phòng chủ quản', required=True)
    employee_id = fields.Many2one('res.users', string='Người bàn giao', default=_default_user, readonly=True)
    company_id = fields.Many2one('res.company', 'Company', index=True, default=lambda self: self.env.company)
    department_id = fields.Many2one('hr.department', 'Phòng ban sử dụng', domain="[('company_id', '=', company_id)]", required=True)
    parent_id = fields.Many2one('hr.employee', 'Quản lý')
    employee_use = fields.Many2one('hr.employee', string='Nhân sự sử dụng', required=True,
                                   domain="[('department_id', 'child_of', department_id)]")

    description = fields.Text(size=600, tracking=True)
    attachment_ids = fields.Many2many('ir.attachment', string='File đính kèm')
    state = fields.Selection([('draft', 'Dự thảo'), ('confirm', 'Xác nhận'), ('approved', 'Nhận hàng')], string='Trạng thái', default='draft',
                             tracking=True)
    device_ids = fields.Many2many('hr.device.main', string='Danh sách thiết bị')
    confirm_id = fields.Many2one('hr.employee', string='Người phê duyệt', readonly=True, copy=False)
    confirm_date = fields.Date(string="Ngày phê duyệt")
    approver_id = fields.Many2one('hr.employee', string='Người nhận', readonly=True, copy=False)
    approver_date = fields.Date(string="Ngày nhận")
    _sql_constraint = [
        ('unique_code', 'unique(code)', 'Code must be unique per equipment'),
    ]

    @api.onchange('department_id')
    def _onchange_department(self):
        self.parent_id = self.department_id.manager_id

    def confirm(self):
        self.state = 'confirm'
        current_employee = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        self.confirm_id = current_employee.id
        self.confirm_date = datetime.now()
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        if self.type == 'import' and self.employee_id:
            action_id = self.env.ref('hrm_maintenance.act_close_ems_equipment_export_view').id
            body = "<p>Dear " + self.employee_id.name + ",</p>"
            body += "<p>Bạn vừa nhận được 1 yêu cầu nhận bàn giao thiết bị.</p>\
                     <p>Chi tiết yêu cầu: <a href='" + base_url + "/web#id=" + str(self.id) + \
                    "&action=" + str(action_id) + \
                    "&model=ems.equipment.export&view_type=form'>Click vào đây</a></p> <hr/> \
                    <b>Mã phiếu bàn giao:</b> " + str(self.code) + "<br/>"
            if self.department_id:
                body += "<b>Phòng ban sử dụng:</b> " + self.department_id.name + "<br/>"
            if self.employee_use:
                body += "<b>Nhân sự bàn giao bàn giao:</b> " + self.employee_use.name + "<br/>"
            body += "<br/><b>Danh sách thiết bị:</b><br/>"
            body += '<table class="table table-striped"><thead><tr><th scope="col">#</th><th scope="col">Tên vật tư</th><th scope="col">Mã vật tư</th><th scope="col">Số serial</th></tr></thead><tbody>'
            idx = 1
            for item in self.device_ids:
                body += '<tr><th scope="row">' + str(idx) + '</th>'
                body += '<td>' + item.name + '</td>'
                body += '<td>' + item.default_code + '</td>'
                body += '<td>' + item.serial_no if item.serial_no else '' + '</td></tr>'
                idx += 1
            body += '</tbody></table>'

            lst_email = []
            if self.category_id.email:
                lst_email.append(self.category_id.email)
            if self.employee_id.work_email:
                lst_email.append(self.employee_id.work_email)
            if len(lst_email) > 0:
                main_employee = {
                    'subject': 'Dilgio-Support: Phiếu nhận bàn giao thiết bị',
                    'body_html': body,
                    'email_to': ",".join(lst_email),
                }
                self.env['mail.mail'].create(main_employee).send()
        else:
            action_id = self.env.ref('hrm_maintenance.act_open_ems_equipment_export_view').id
            body = "<p>Dear " + self.employee_use.name + ",</p>"
            body += "<p>Bạn vừa nhận được 1 yêu cầu bàn giao thiết bị.</p>\
                     <p>Chi tiết yêu cầu: <a href='" + base_url + "/web#id=" + str(self.id) + \
                    "&action=" + str(action_id) + \
                    "&model=ems.equipment.export&view_type=form'>Click vào đây</a></p> <hr/> \
                    <b>Mã phiếu bàn giao:</b> " + str(self.code) + "<br/>"
            if self.category_id:
                body += "<b>Bộ phận phụ trách:</b> " + self.category_id.name + "<br/>"
            if self.employee_id:
                body += "<b>Người bàn giao:</b> " + self.employee_id.name + "<br/>"
            body += "<br/><b>Danh sách thiết bị:</b><br/>"
            body += '<table class="table table-striped"><thead><tr><th scope="col">#</th><th scope="col">Tên vật tư</th><th scope="col">Mã vật tư</th><th scope="col">Số serial</th></tr></thead><tbody>'
            idx = 1
            for item in self.device_ids:
                body += '<tr><th scope="row">' + str(idx) + '</th>'
                body += '<td>' + item.name + '</td>'
                body += '<td>' + item.default_code + '</td>'
                body += '<td>' + item.serial_no if item.serial_no else '' + '</td></tr>'
                idx += 1
            body += '</tbody></table>'

            lst_email = []
            if self.department_id.manager_id.work_email:
                lst_email.append(self.department_id.manager_id.work_email)
            if self.employee_use.work_email:
                lst_email.append(self.employee_use.work_email)
            if len(lst_email) > 0:
                main_employee = {
                    'subject': 'Support: Phiếu bàn giao thiết bị',
                    'body_html': body,
                    'email_to': ",".join(lst_email),
                }
                self.env['mail.mail'].create(main_employee).send()

    def approve(self):
        self.state = 'approved'
        current_employee = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        self.approver_id = current_employee.id
        self.approver_date = datetime.now()

        for item in self.device_ids:
            if self.type == 'export':
                item.activate = 'usage'
                item.company_id = self.company_id.id
                item.department_id = self.department_id.id
                item.parent_id = self.parent_id.id
                item.employee_id = self.employee_use.id
                for ex in item.extra_device_ids:
                    if ex.activate == 'not_used':
                        ex.activate = 'usage'
            else:
                item.activate = 'not_used'
                item.department_id = None
                item.parent_id = None
                item.employee_id = None
                for ex in item.extra_device_ids:
                    if ex.activate == 'usage':
                        ex.activate = 'not_used'

    def _compute_attachment_ids(self):
        for task in self:
            attachment_ids = self.env['ir.attachment'].search([('res_id', '=', task.id), ('res_model', '=', 'ems.equipment.export')]).ids
            message_attachment_ids = task.mapped('message_ids.attachment_ids').ids  # from mail_thread
            task.attachment_ids = list(set(attachment_ids) - set(message_attachment_ids))

    @api.constrains('code')
    def _compute_special_character_code(self):
        for record in self:
            if not re.match("^[a-zA-Z0-9_/\\\\]*$", record.code):
                raise ValidationError(_("Please Provide valid Code."))

    @api.onchange('code')
    def _compute_upper_code(self):
        for record in self:
            if record.code:
                code = record.code
                record.code = code.upper()

    @api.model
    def create(self, vals):
        res = super(EmsEquipmentExport, self).create(vals)
        if vals.get('state') == 'confirm':
            EmsEquipmentExport.confirm(res)
        return res