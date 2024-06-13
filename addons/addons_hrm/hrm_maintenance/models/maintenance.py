# -*- coding: utf-8 -*-

import datetime
from datetime import timedelta
import pytz
from odoo.http import request
from odoo import api, fields, models, SUPERUSER_ID, _
import string
import random
from random import randint
from odoo.exceptions import ValidationError
from odoo.exceptions import UserError
from odoo.addons.base.models.res_partner import _tz_get
import time


class MaintenanceEquipmentCategory(models.Model):
    _name = 'hr.maintenance.equipment.category'
    _description = 'Maintenance Equipment Category'

    department_id = fields.Many2one('hr.department', 'Phòng ban quản lý')
    name = fields.Char('Category Name', required=True, translate=True)
    email = fields.Char('Email')
    technician_user_id = fields.Many2one('hr.employee', 'Chịu trách nhiệm',
                                         domain="[('department_id', 'child_of', department_id)]")
    color = fields.Integer('Color Index')
    note = fields.Text('Comments', translate=True)

    equipment_ids = fields.One2many('hr.device.main', 'category_id', string='Thiết bị')
    equipment_count = fields.Integer(string="Equipment", compute='_compute_equipment_count')
    maintenance_ids = fields.One2many('hr.maintenance.request', 'category_id', copy=False)
    maintenance_count = fields.Integer(string="Maintenance Count", compute='_compute_maintenance_count')
    team_ids = fields.One2many('hr.maintenance.team', 'maintenance_category_id', string='Family',
                               help='Family Information')
    team_count = fields.Integer(compute='_compute_team_count')

    @api.onchange('department_id')
    def _onchange_department(self):
        self.name = self.department_id.name

    # count of all custody contracts
    def _compute_team_count(self):
        for each in self:
            custody_ids = self.env['hr.maintenance.team'].search([('maintenance_category_id', '=', each.id)])
            each.team_count = len(custody_ids)

    def _compute_equipment_count(self):
        equipment_data = self.env['hr.device.main'].read_group([('category_id', 'in', self.ids)], ['category_id'],
                                                                ['category_id'])
        mapped_data = dict([(m['category_id'][0], m['category_id_count']) for m in equipment_data])
        for category in self:
            category.equipment_count = mapped_data.get(category.id, 0)

    def _compute_maintenance_count(self):
        maintenance_data = self.env['hr.maintenance.request'].read_group([('category_id', 'in', self.ids)],
                                                                          ['category_id'], ['category_id'])
        mapped_data = dict([(m['category_id'][0], m['category_id_count']) for m in maintenance_data])
        for category in self:
            category.maintenance_count = mapped_data.get(category.id, 0)


class MaintenanceEquipment(models.Model):
    _inherit = 'hr.device.main'

    category_id = fields.Many2one('hr.maintenance.equipment.category', 'BP quản lý/bảo trì')
    team_id = fields.Many2one('hr.maintenance.team', string='Đội phụ trách',
                              domain="[('maintenance_category_id', '=', category_id)]")
    maintenance_ids = fields.One2many('hr.maintenance.request', 'equipment_id')
    maintenance_count = fields.Integer(compute='_compute_maintenance_count', string="Tổng số yêu cầu sửa chữa")
    certificate_count = fields.Integer(compute='_compute_maintenance_count', string="Tổng số bảo dưỡng định kỳ")
    custody_ids = fields.Many2many('ems.equipment.export', string="Danh sách bàn giao",
                                   domain=[('state', '=', 'approved')])

    @api.depends('maintenance_ids')
    def _compute_maintenance_count(self):
        for item in self:
            item.maintenance_count = len(item.maintenance_ids.filtered(lambda m: m.maintenance_type == 'corrective'))
            item.certificate_count = len(item.maintenance_ids.filtered(lambda m: m.maintenance_type == 'preventive'))

    @api.model
    def update_maintenance(self):
        data = self.search([('activate', '=', 'usage')])
        for record in data:
            if record.first_date_use:
                first_date_use = record.first_date_use
                # Bảo dưỡng định kỳ
                if datetime.datetime.now().date() == record.maintenance_expire_date:
                    payload = {
                        'name': "Bảo dưỡng định kỳ: " + '[' + record.default_code + '] ' + record.name,
                        'code': record.default_code,
                        'maintenance_type': 'preventive',
                        'description': "Yêu cầu bảo dưỡng định kỳ",
                        'category_id': record.category_id.id if record.category_id else None,
                        'priority': '2',
                        'equipment_id': record.id,
                        'request_date': datetime.datetime.now(),
                        'person_name': record.employee_id.name if record.employee_id else None,
                        'email': record.employee_id.work_email if record.employee_id else None,
                        'phone': record.employee_id.work_phone if record.employee_id else None,
                        'department': record.department_id.name if record.department_id else None,
                    }
                    self.env['hr.maintenance.request'].create(payload)
                # Bảo hành
                if record.period:
                    date = first_date_use
                    deadline_repair = self.count_deadline(date, 'months', record.period)
                    days = deadline_repair['days']
                    if days == 0:
                        record.activate = 'out_of_warranty'
        return True

    def approve(self):
        for item in self:
            item.activate = 'not_used'
            item.department_id = None
            item.parent_id = None
            item.employee_id = None
            for ex in item.extra_device_ids:
                if ex.activate == 'usage':
                    ex.activate = 'not_used'


class HRMaintenanceRequest(models.Model):
    _name = 'hr.maintenance.request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Maintenance Request'
    _order = "id desc"

    state = fields.Selection([('new', '	Yêu cầu mới'),
                              ('doing', 'Đang thực hiện'),
                              ('done', '	Hoàn thành'),
                              ('cancel', 'Hủy'),
                              ('closed', 'Đóng')],
                             default='new', string='Trạng thái')
    name = fields.Char('Subjects', required=True, states={'new': [('readonly', False)]}, readonly=True)
    code = fields.Char('Code', readonly=True)
    channel = fields.Selection([('website', 'Website'), ('email', 'Email'), ('phone', 'Phone'), ('other', 'Khác')],
                               default='email',
                               string='Nguồn/Kênh', states={'new': [('readonly', False)]}, readonly=True)
    person_name = fields.Many2one('hr.employee', string='Người yêu cầu', states={'new': [('readonly', False)]},
                                  readonly=True)
    email = fields.Char(string="Email", states={'new': [('readonly', False)]}, readonly=True)
    phone = fields.Char(string="Điện thoại", states={'new': [('readonly', False)]}, readonly=True)
    department = fields.Char(string="Phòng ban", states={'new': [('readonly', False)]}, readonly=True)
    description = fields.Html('Mô tả', states={'new': [('readonly', False)]}, readonly=True)
    type = fields.Selection([('pc', 'PC'),
                             ('erp', 'ERP'),
                             # ('onetouch', 'One Touch'),
                             # ('informatics_equipment', 'Informatics equipment'),
                             # ('external_access', 'External access'),
                             ('website', 'Website'),
                             ('security', 'Security')], default='erp',
                            string='Type maintenance')
    request_date = fields.Datetime('Ngày yêu cầu', default=lambda self: fields.Datetime.now(), tracking=True,
                                   help="Date requested for the maintenance to happen")
    equipment_id = fields.Many2one('hr.device.main', 'Thiết bị/Vật tư', tracking=True)
    category_id = fields.Many2one('hr.maintenance.equipment.category', 'Bộ phận tiếp nhận', required=True,
                                  tracking=True, states={'new': [('readonly', False)]}, readonly=True)
    maintenance_team_id = fields.Many2one('hr.maintenance.team', string='Đội tiếp nhận',
                                          states={'new': [('readonly', False)]}, readonly=True)
    emp_id = fields.Many2one('hr.employee', string='Người phụ trách')
    priority = fields.Selection(related='area_type_maintenance_request.priority')
    support_rating = fields.Selection(
        [('1', 'Rất tệ'), ('2', 'Tệ'), ('3', 'Bình thường'), ('4', 'Tốt'), ('5', 'Rất tốt')], string='Đánh giá')
    color = fields.Integer('Color Index')
    close_date = fields.Datetime('Ngày đóng', help="Ngày bảo trì hoàn thành. ", compute='calculation_close_date',
                                 store=True)
    kanban_state = fields.Selection(
        [('normal', 'In Progress'), ('doing', 'Doing'), ('blocked', 'Blocked'), ('done', 'Ready for next stage')],
        string='Kanban State', required=True, default='normal', tracking=True)
    supervisor_ids = fields.Many2many('hr.employee', string='Danh sách nhân sự bảo trì',
                                      tracking=True, domain="[('active','=','usage')]")
    archive = fields.Boolean(default=False,
                             help="Set archive to true to hide the maintenance request without deleting it.")
    maintenance_type = fields.Selection([('corrective', 'Khắc phục sự cố'), ('preventive', 'Bảo dưỡng định kỳ')],
                                        string='Loại bảo trì', default="corrective", readonly=True)
    schedule_date = fields.Datetime('Lịch hẹn', help="Ngày nhóm bảo trì lên kế hoạch bảo trì ")
    tools_description = fields.Html('Hiện trạng', translate=True)
    operations_description = fields.Html('Kết quả', translate=True)
    status = fields.Text('Tình trạng', compute="_compute_status")
    attachment_ids = fields.Many2many('ir.attachment', string='File đính kèm')
    portal_access_key = fields.Char(string="Portal Access Key")
    support_comment = fields.Text(string="Support Comment")
    close_comment = fields.Html(string="Close Comment")
    closed_by_id = fields.Many2one('res.users', string="Closed By")
    time_to_close = fields.Integer(string="Time to close (seconds)")
    type_maintenance_request = fields.Many2one('type.maintenance.request', string='Type maintenance request',
                                               states={'new': [('readonly', False)]}, readonly=True)
    area_type_maintenance_request = fields.Many2one('area.type.maintenance.request',
                                                    states={'new': [('readonly', False)]}, readonly=True,
                                                    string='area type maintenance request')
    the_average_time = fields.Integer(related='area_type_maintenance_request.the_average_time')
    completion_time = fields.Char('Thời gian hoàn thành')
    wizard_result_id = fields.Many2many('maintenance.request.get.result')
    result_id = fields.Many2many('maintenance.request.reason')
    survey_url = fields.Char('Survey URL')
    base_url = fields.Char('Base URL')

    default_cc = fields.Text('Cc (Emails)', help='Carbon copy message recipients (Emails)',
                             states={'new': [('readonly', False)]}, readonly=True)
    default_bcc = fields.Char('Bcc (Emails)', help='Blind carbon copy message recipients (Emails)',
                              states={'new': [('readonly', False)]}, readonly=True)

    template_id = fields.Many2one('mail.template', string='Email Template',
                                  compute='_compute_send_mail', store=True, readonly=False,
                                  domain="[('model', '=', 'hr.maintenance.request')]")
    mail_tz = fields.Selection(_tz_get, compute='_compute_mail_tz',
                               help='Timezone used for displaying time in the mail template')
    reason_change = fields.Char('Lí do thay đổi người phụ trách')
    completed_process = fields.Integer('Completed process')
    deadline = fields.Datetime('Deadline')

    @api.constrains('the_average_time', 'request_date')
    def get_deadline(self):
        for record in self:
            if record.the_average_time and record.request_date:
                record.deadline = record.request_date + timedelta(minutes=record.the_average_time)

    def _compute_mail_tz(self):
        for attendee in self:

            if attendee.message_partner_ids:
                attendee.mail_tz = attendee.message_partner_ids[0].tz
            else:
                attendee.mail_tz = attendee.person_name.user_partner_id.tz

    @api.depends('result_id')
    def _compute_send_mail(self):
        for record in self:
            template = record.result_id.template_id
            record.template_id = template

    @api.onchange('person_name')
    def onchange_person_name(self):
        for rec in self:
            if rec.person_name:
                rec.email = rec.person_name.work_email
                rec.phone = rec.person_name.mobile_phone
                rec.department = rec.person_name.department_id.name

    @api.depends('schedule_date')
    def _compute_status(self):
        for record in self:
            if record.state in ['new', 'doing']:
                msg = ''
                time = datetime.datetime.now()
                tz_current = pytz.timezone(self._context.get('tz') or 'UTC')  # get timezone user
                tz_database = pytz.timezone('UTC')
                time = tz_database.localize(time)
                time = time.astimezone(tz_current)
                time = time.date()
                if record.schedule_date:
                    expected_date = record.schedule_date.date()
                    days = (expected_date - time).days
                    if days < 0:
                        msg += ('- Quá hạn hoàn thành %s ngày') % abs(days)
                    elif days == 0:
                        msg += ('- Hôm nay là hạn chót')
                    elif days < 7:
                        msg += ('- Còn %s ngày đến hạn hoàn thành') % abs(days)
            elif record.state == 'done':
                msg = '- Đã hoàn thành'
            elif record.state == 'cancel':
                msg = '- Đã hủy'
            else:
                msg = '- Yêu cầu đã được đóng'
            record.status = msg

    @api.onchange('category_id')
    def _onchange_category_id(self):
        if self.category_id.department_id:
            return {
                'domain': {'emp_id': [('department_id', 'child_of', self.category_id.department_id.id)],
                           'maintenance_team_id': [('maintenance_category_id', '=', self.category_id.id)]}
            }

    @api.onchange('maintenance_team_id')
    def _onchange_maintenance_team_id(self):
        self.emp_id = self.maintenance_team_id.technician_user_id

    def archive_equipment_request(self):
        self.write({'archive': True})

    @api.model
    def create(self, vals):
        # context: no_log, because subtype already handle this
        if vals.get('emp_id'):
            vals['state'] = 'doing'
        vals['code'] = self.env['ir.sequence'].next_by_code('maintenance.code.action')
        request = super(HRMaintenanceRequest, self).create(vals)
        request.portal_access_key = randint(1000000000, 2000000000)
        survey_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        request.survey_url = survey_url + "/support/survey/" + request.portal_access_key
        if request.the_average_time:
            request.completed_process = request.the_average_time

        return request

    def rpc_render_completed_process(self, progress):
        self.completed_process = 0

    def write(self, vals):
        if vals.get('emp_id'):
            vals['state'] = 'doing'
        super(HRMaintenanceRequest, self).write(vals)

    @api.constrains('state')
    def send_mail_confirm(self):
        if self.state == 'doing':
            survey_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            self.base_url = survey_url + '/web#id=%d&view_type=form&model=%s' % (self.id, self._name)

            template = self.env.ref('hrm_maintenance.email_template_data_maintenance_receive')
            template2 = self.env.ref('hrm_maintenance.email_template_data_maintenance_new')
            for record in self:
                self.env['mail.thread'].message_post_with_template(
                    template.id,
                    res_id=record.id,
                    model=record._name,
                )
                self.env['mail.thread'].message_post_with_template(
                    template2.id,
                    res_id=record.id,
                    model=record._name,
                )

    def open_close_ticket_wizard(self):
        if not self.email:
            raise UserError(_("The requestor's email is not available. Please provide the requester's email."))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Kết quả yêu cầu'),
            'res_model': 'maintenance.request.get.result',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_maintenance_ids': self.ids, 'active_test': False},
            'views': [[False, 'form']]
        }

    @api.onchange('type', 'type_maintenance_request')
    def clear_type_maintenance_request(self):
        if self.type != self.type_maintenance_request.type:
            self.type_maintenance_request = False
            self.area_type_maintenance_request = False
        elif self.type_maintenance_request != self.area_type_maintenance_request.type_maintenance_request:
            self.area_type_maintenance_request = False


class MaintenanceTeam(models.Model):
    _name = 'hr.maintenance.team'
    _description = 'Maintenance Teams'

    name = fields.Char(required=True, translate=True)
    active = fields.Boolean(default=True)
    maintenance_category_id = fields.Many2one('hr.maintenance.equipment.category', string='Bộ phận tiếp nhận',
                                              required=True)
    technician_user_id = fields.Many2one('hr.employee', 'Chịu trách nhiệm')
    member_ids = fields.Many2many('hr.employee', string="Thành viên")
    color = fields.Integer("Color Index", default=0)
    request_ids = fields.One2many('hr.maintenance.request', 'maintenance_team_id', copy=False)

    # For the dashboard only
    todo_request_count = fields.Integer(string="Number of Requests", compute='_compute_todo_requests')
    todo_request_count_date = fields.Integer(string="Number of Requests Scheduled", compute='_compute_todo_requests')
    todo_request_count_block = fields.Integer(string="Number of Requests Blocked", compute='_compute_todo_requests')

    @api.onchange('maintenance_category_id')
    def _onchange_department(self):
        if self.maintenance_category_id.department_id:
            return {
                'domain': {'technician_user_id': [
                    ('department_id', 'child_of', self.maintenance_category_id.department_id.id)],
                           'member_ids': [('department_id', 'child_of', self.maintenance_category_id.department_id.id)]}
            }

    @api.depends('request_ids.state')
    def _compute_todo_requests(self):
        for item in self:
            item.todo_request_count = len(item.request_ids.filtered(lambda e: e.kanban_state != 'done'))
            item.todo_request_count_date = len(item.request_ids)
            item.todo_request_count_block = len(item.request_ids.filtered(lambda e: e.kanban_state == 'done'))

    @api.depends('equipment_ids')
    def _compute_equipment(self):
        for item in self:
            item.equipment_count = len(item.equipment_ids)


class TypeMaintenanceRequest(models.Model):
    _name = 'type.maintenance.request'

    name = fields.Char('name', required=True)
    area = fields.One2many('area.type.maintenance.request', 'type_maintenance_request', string='area')
    type = fields.Selection([('pc', 'PC'),
                             ('erp', 'ERP'),
                             # ('onetouch', 'One Touch'),
                             # ('informatics_equipment', 'Informatics equipment'),
                             # ('external_access', 'External access'),
                             ('website', 'Website'),
                             ('security', 'Security'), ], default='erp',
                            string='Type maintenance')


class AreaTypeMaintenanceRequest(models.Model):
    _name = 'area.type.maintenance.request'

    def get_code(self):
        size = 8
        chars = string.ascii_uppercase + string.digits
        return ''.join(random.choice(chars) for _ in range(size))

    code = fields.Char('Code', default=get_code, readonly=True)
    type_maintenance_request = fields.Many2one('type.maintenance.request', string='Type maintenance request')
    name = fields.Char('Name', required=True)
    the_average_time = fields.Integer('Average time')
    priority = fields.Selection(
        [('0', 'Rất thấp'), ('1', 'Thấp'), ('2', 'Bình thường'), ('3', 'Cao'), ('4', 'Rất cao'), ('5', 'Thương lượng')],
        string='Độ ưu tiên', required=True)


class ApplicantRefuseReason(models.Model):
    _name = "maintenance.request.reason"
    _description = 'Refuse Reason of Maintenance Request'

    name = fields.Char('Description', required=True, translate=True)
    template_id = fields.Many2one('mail.template', string='Email Template',
                                  domain="[('model', '=', 'hr.maintenance.request')]")
    active = fields.Boolean('Active', default=True)


class MailComposer(models.TransientModel):
    _inherit = 'mail.compose.message'

    email_bcc = fields.Char('Email BCC')
    email_cc = fields.Char('Email CC')

    def _onchange_template_id(self, template_id, composition_mode, model, res_id):
        """ - mass_mailing: we cannot render, so return the template values
            - normal mode: return rendered values
            /!\ for x2many field, this onchange return command instead of ids
        """
        self.email_bcc = self.email_cc = self.reply_to = ''

        if template_id and composition_mode == 'mass_mail':
            template = self.env['mail.template'].browse(template_id)
            fields = ['subject', 'body_html', 'email_from', 'reply_to', 'mail_server_id']
            values = dict((field, getattr(template, field)) for field in fields if getattr(template, field))
            if template.attachment_ids:
                values['attachment_ids'] = [att.id for att in template.attachment_ids]
            if template.mail_server_id:
                values['mail_server_id'] = template.mail_server_id.id
        elif template_id:
            if template_id == self.env.ref("hrm_maintenance.email_template_data_maintenance_new").id:
                ls = ['subject', 'body_html', 'email_from', 'email_to', 'partner_to',
                      'attachment_ids', 'mail_server_id']
            elif template_id == self.env.ref("hrm_maintenance.email_template_data_maintenance_refuse").id:
                ls = ['subject', 'body_html', 'email_from', 'email_to', 'partner_to', 'email_cc', 'email_bcc',
                      'reply_to',
                      'attachment_ids', 'mail_server_id']
            elif template_id == self.env.ref("hrm_maintenance.email_template_data_maintenance_receive").id:
                ls = ['subject', 'body_html', 'email_from', 'email_to', 'partner_to',
                      'attachment_ids', 'mail_server_id']
            elif template_id == self.env.ref("hrm_maintenance.email_template_data_maintenance_complete").id:
                ls = ['subject', 'body_html', 'email_from', 'email_to', 'partner_to', 'email_cc', 'email_bcc',
                      'reply_to',
                      'attachment_ids', 'mail_server_id']
            else:
                ls = ['subject', 'body_html', 'email_from', 'email_to', 'partner_to',
                      'reply_to', 'attachment_ids', 'mail_server_id']
            values = self.generate_email_for_composer(
                template_id, [res_id], ls)[res_id]
            # transform attachments into attachment_ids; not attached to the document because this will
            # be done further in the posting process, allowing to clean database if email not send
            attachment_ids = []
            Attachment = self.env['ir.attachment']
            for attach_fname, attach_datas in values.pop('attachments', []):
                data_attach = {
                    'name': attach_fname,
                    'datas': attach_datas,
                    'res_model': 'mail.compose.message',
                    'res_id': 0,
                    'type': 'binary',  # override default_type from context, possibly meant for another model!
                }
                attachment_ids.append(Attachment.create(data_attach).id)
            # if values.get('attachment_ids', []) or attachment_ids:
            #     values['attachment_ids'] = [self.Command.set(values.get('attachment_ids', []) + attachment_ids)]
        else:
            default_values = self.with_context(default_composition_mode=composition_mode, default_model=model,
                                               default_res_id=res_id).default_get(
                ['composition_mode', 'model', 'res_id', 'parent_id', 'partner_ids', 'subject', 'body', 'email_from',
                 'reply_to', 'attachment_ids', 'mail_server_id'])
            values = dict((key, default_values[key]) for key in
                          ['subject', 'body', 'partner_ids', 'email_from', 'reply_to', 'attachment_ids',
                           'mail_server_id'] if key in default_values)

        if values.get('body_html'):
            values['body'] = values.pop('body_html')

        # This onchange should return command instead of ids for x2many field.
        values = self._convert_to_write(values)

        return {'value': values}
