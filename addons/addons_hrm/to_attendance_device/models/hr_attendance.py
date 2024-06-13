import dateutil.rrule
import pytz

from odoo import models, fields, api
from datetime import datetime, timedelta
from odoo.exceptions import ValidationError

class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    def _get_employee_id(self):
        employee_rec = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        return employee_rec.id

    checkin_device_id = fields.Many2one('attendance.device', string='Checkin Device', readonly=True, index=True,
                                        help='The device with which user took check in action')
    checkout_device_id = fields.Many2one('attendance.device', string='Checkout Device', readonly=True, index=True,
                                         help='The device with which user took check out action')
    activity_id = fields.Many2one('attendance.activity', string='Attendance Activity',
                                  help='This field is to group attendance into multiple Activity (e.g. Overtime, Normal Working, etc)')
    company_id = fields.Many2one('res.company', 'Company', related="employee_id.company_id", readonly=True, store= True)

    department_id = fields.Many2one('hr.department', string="Department", related="employee_id.department_id",
                                    readonly=True, store= True)
    time_workday = fields.Float('Giải trình giờ công', readonly=True, states={'draft': [('readonly', False)]})
    overtime = fields.Float('OT', readonly=True, states={'draft': [('readonly', False)]})
    reason = fields.Text(string="Giải trình", help='Giải trình những trường hợp quên chấm, lý do dữ liệu không khớp...')
    name = fields.Char(default='X', string='Loại công')
    state = fields.Selection([
        ('draft', 'Chưa xác nhận'),
        ('confirm', 'Xác nhận'),
        ('refuse', 'Từ chối'),
        ('validate', 'Đã phê duyệt')
    ], string='Trạng thái', readonly=True, tracking=True, copy=False, default='draft')
    approver_id = fields.Many2one('hr.employee', string='Người phê duyệt', readonly=True, copy=False, default=_get_employee_id)
    resign_confirm_date = fields.Datetime(string="Ngày phê duyệt", default=datetime.now())
    worked_hours_real = fields.Float(string='Worked Hours', compute='_compute_worked_hours_real', readonly=True, store=True)
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    date_attendance = fields.Date("Date attendance", compute='_compute_get_date', store= True)

    @api.depends('check_in')
    def _compute_get_date(self):
        for attendance in self:
            tz = pytz.timezone('Asia/Ho_Chi_Minh')
            attendance.date_attendance = attendance.check_in.astimezone(tz).date()

    @api.depends('check_in', 'check_out')
    def _compute_worked_hours_real(self):
        for attendance in self:
            if attendance.check_out and attendance.check_in:
                if attendance.check_in and attendance.check_out:
                    check_out_real = attendance.check_out
                    check_in_real = attendance.check_in
                    stday = fields.date.weekday(check_in_real)
                    if check_out_real > datetime.replace(check_out_real, hour=10, minute=10):
                        check_out_real = datetime.replace(check_out_real, hour=10, minute=10)
                    if check_in_real < datetime.replace(check_in_real, hour=1):
                        check_in_real = datetime.replace(check_in_real, hour=1, minute=00)
                    delta = check_out_real - check_in_real
                    attendance.worked_hours_real = round(delta.total_seconds() / 3600, 1)
                    if attendance.days[stday] != attendance.days[5]:
                        if attendance.worked_hours_real >= 5:
                            attendance.worked_hours_real = attendance.worked_hours_real - 1
                        if attendance.worked_hours_real >= 8.0:
                            attendance.worked_hours_real = 8.0
                            attendance.state = 'validate'
                        if attendance.worked_hours_real < 0:
                            attendance.worked_hours_real = 0
                    if attendance.days[stday] == attendance.days[5] and attendance.worked_hours_real >= 4.0:
                        attendance.state = 'validate'
                        attendance.worked_hours_real = 8
            else:
                attendance.worked_hours_real = False

    @api.constrains('check_in', 'check_out', 'employee_id')
    def _check_validity(self):
        if not self.env.context.get('synch_ignore_constraints', False):
            super(HrAttendance, self)._check_validity()

    @api.constrains('time_workday')
    def _check_time_workday_value(self):
        for item in self:
            if not 0 <= item.time_workday <= 8:
                raise ValidationError("Giải trình giờ công không hợp lệ!!!")

    def action_attendance_approve(self):
        atten = self.env['hr.attendance'].sudo().search([])
        for attendance in atten:
            tz = pytz.timezone('Asia/Ho_Chi_Minh')
            attendance.date_attendance = attendance.check_in.astimezone(tz).date()
        current_employee = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        self.write({'state': 'validate', 'approver_id': current_employee.id, 'resign_confirm_date': datetime.now(), 'worked_hours_real': self.time_workday})
        return True

    def action_attendance_refuse(self):
        current_employee = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        self.write({'state': 'refuse', 'approver_id': current_employee.id, 'resign_confirm_date': datetime.now()})
        return True

    def action_attendance_cancel(self):
        current_employee = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        self.write({'state': 'draft', 'approver_id': current_employee.id, 'resign_confirm_date': datetime.now()})

        return True

    def name_get(self):
        res = super(HrAttendance, self).name_get()
        if self.env.context.get('show_name'):
            return [(attendance.id, attendance.name) for attendance in self]
        return res