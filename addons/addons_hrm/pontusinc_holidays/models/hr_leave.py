import calendar
import logging
import pytz
import math
import builtins
from odoo.addons.base.models.ir_model import MODULE_UNINSTALL_FLAG

from collections import namedtuple, defaultdict
from datetime import datetime, timedelta, time

from odoo.exceptions import UserError
from odoo.tools import float_utils
from odoo.tools.translate import _
from pytz import timezone, UTC
from math import ceil
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, tools
from odoo.tools.float_utils import float_compare
from odoo.exceptions import ValidationError
from odoo.tools.misc import format_date

DummyAttendance = namedtuple('DummyAttendance', 'hour_from, hour_to, dayofweek, day_period, week_type')

_logger = logging.getLogger(__name__)
HOURS_PER_DAY = 8
# This will generate 16th of days
ROUNDING_FACTOR = 16


def float_to_time(float_hours):
    hours = int(float_hours)
    minutes = int((float_hours * 60) % 60)
    time_delta = timedelta(hours=hours, minutes=minutes)
    base_date = datetime(1900, 1, 1)
    result_datetime = base_date + time_delta

    return result_datetime.time()


def combine_date_and_time(date_obj, time_obj):
    return datetime.combine(date_obj, time_obj)


def float_round(value, precision_digits=None, precision_rounding=None, rounding_method='HALF-UP'):
    rounding_factor = _float_check_precision(precision_digits=precision_digits,
                                             precision_rounding=precision_rounding)
    if rounding_factor == 0 or value == 0:
        return 0.0

    normalized_value = value / rounding_factor  # normalize
    sign = math.copysign(1.0, normalized_value)
    epsilon_magnitude = math.log(abs(normalized_value), 2)
    epsilon = 2 ** (epsilon_magnitude - 52)

    if rounding_method == 'UP':
        normalized_value -= sign * epsilon
        rounded_value = math.ceil(abs(normalized_value)) * sign

    elif rounding_method == 'DOWN':
        normalized_value += sign * epsilon
        rounded_value = math.floor(abs(normalized_value)) * sign

    # TIE-BREAKING: HALF-EVEN
    # We want to apply HALF-EVEN tie-breaking rules, i.e. 0.5 rounds towards closest even number.
    elif rounding_method == 'HALF-EVEN':
        rounded_value = math.copysign(builtins.round(normalized_value), normalized_value)

    # TIE-BREAKING: HALF-DOWN
    # We want to apply HALF-DOWN tie-breaking rules, i.e. 0.5 rounds towards 0.
    elif rounding_method == 'HALF-DOWN':
        normalized_value -= math.copysign(epsilon, normalized_value)
        rounded_value = round(normalized_value)

    # TIE-BREAKING: HALF-UP (for normal rounding)
    # We want to apply HALF-UP tie-breaking rules, i.e. 0.5 rounds away from 0.
    else:
        normalized_value += math.copysign(epsilon, normalized_value)
        rounded_value = round(normalized_value)  # round to integer

    result = rounded_value * rounding_factor  # de-normalize
    return result


def _float_check_precision(precision_digits=None, precision_rounding=None):
    assert (precision_digits is not None or precision_rounding is not None) and \
           not (precision_digits and precision_rounding), \
        "exactly one of precision_digits and precision_rounding must be specified"
    assert precision_rounding is None or precision_rounding > 0, \
        "precision_rounding must be positive, got %s" % precision_rounding
    if precision_digits is not None:
        return 10 ** -precision_digits
    return precision_rounding


def float_to_time(hours):
    """ Convert a number of hours into a time object. """
    if hours == 24.0:
        return time.max
    fractional, integral = math.modf(hours)
    return time(int(integral), int(float_round(60 * fractional, precision_digits=0)), 0)


def get_saturdays(month, year):
    cal = calendar.monthcalendar(year, month)
    saturdays = [week[calendar.SATURDAY] for week in cal if week[calendar.SATURDAY] != 0]
    return saturdays


class HolidaysRequest(models.Model):
    _inherit = 'hr.leave'

    @api.model
    def default_get(self, fields_list):
        defaults = super(HolidaysRequest, self).default_get(fields_list)
        defaults = self._default_get_request_dates(defaults)
        defaults['holiday_status_id'] = False
        lt = self.env['hr.leave.type']
        if self.env.context.get('holiday_status_display_name',
                                True) and 'holiday_status_id' in fields_list and not defaults.get('holiday_status_id'):
            lt = self.env['hr.leave.type'].search(
                ['|', ('requires_allocation', '=', 'no'), ('has_valid_allocation', '=', True)], limit=1,
                order='sequence')
            if lt:
                defaults['holiday_status_id'] = lt.id
                defaults['request_unit_custom'] = False

        if 'state' in fields_list and not defaults.get('state'):
            defaults['state'] = 'confirm' if lt.leave_validation_type != 'no_validation' else 'draft'

        if 'request_date_from' in fields_list and 'request_date_from' not in defaults:
            defaults['request_date_from'] = fields.Date.today()
        if 'request_date_to' in fields_list and 'request_date_to' not in defaults:
            defaults['request_date_to'] = fields.Date.today()

        return defaults

    def _default_get_request_dates(self, values):
        client_tz = timezone(self._context.get('tz') or self.env.user.tz or 'UTC')
        if values.get('date_from'):
            if not values.get('request_date_from'):
                values['request_date_from'] = pytz.utc.localize(values['date_from']).astimezone(client_tz)
            del values['date_from']
        if values.get('date_to'):
            if not values.get('request_date_to'):
                values['request_date_to'] = pytz.utc.localize(values['date_to']).astimezone(client_tz)
            del values['date_to']
        return values

    is_user_only_responsible = fields.Boolean(compute="_compute_is_user_only_responsible")
    number_of_hours = fields.Float(
        'Duration (Hours)', compute='_compute_duration', store=True, tracking=True,
        help='Number of hours of the time off request. Used in the calculation.')
    last_several_days = fields.Boolean("All day", compute="_compute_last_several_days")
    leave_type_increases_duration = fields.Boolean(compute='_compute_leave_type_increases_duration')
    company_id = fields.Many2one('res.company', compute='_compute_company_id', store=True)
    resource_calendar_id = fields.Many2one('resource.calendar', compute='_compute_resource_calendar_id', store=True,
                                           readonly=False, copy=False)

    time_custom = fields.Boolean(default=False, string='Time Details',
                                 help="Allows you to choose actual detailed times")
    from_time = fields.Float(string='From Time', default=8.59)
    to_time = fields.Float(string='To Time', default=18.0)

    request_date_from_display = fields.Char(compute="_compute_request_date_display", )
    request_date_to_display = fields.Char(compute='_compute_request_date_display', )

    @api.depends('holiday_status_id')
    def _compute_state(self):
        for leave in self:
            leave.state = 'confirm' if leave.validation_type != 'no_validation' and not leave.holiday_status_id.is_draft else 'draft'

    @api.model
    def rpc_update_status(self, id, type_option):
        if id and type_option == 'send':
            self.browse(id).write({'state': 'confirm'})

    @api.depends('request_date_from', 'request_date_to')
    def _compute_request_date_display(self):
        lang = self.env.lang or 'en_US'
        for rec in self:
            if rec.request_date_from:
                if lang == 'vi_VN':
                    rec.request_date_from_display = str(rec.request_date_from.day) + ' tháng ' + str(
                        rec.request_date_from.month) + ' năm ' + str(rec.request_date_from.year) + ' '
                else:
                    rec.request_date_from_display = str(rec.request_date_from.day) + ' month ' + str(
                        rec.request_date_from.month) + ' year ' + str(rec.request_date_from.year) + ' '
            if rec.request_date_to:
                if lang == 'vi_VN':
                    rec.request_date_to_display = str(rec.request_date_to.day) + ' tháng ' + str(
                            rec.request_date_to.month) + ' năm ' + str(rec.request_date_to.year) + ' '
                else:
                    rec.request_date_to_display = str(rec.request_date_to.day) + ' month ' + str(
                        rec.request_date_to.month) + ' year ' + str(rec.request_date_to.year) + ' '


    @tools.ormcache('stday', 'employee', 'type')
    def get_day_of_week_morning(self, stday, employee, type):
        morning = employee.resource_calendar_id.attendance_ids.search([('dayofweek', '=', str(stday)),
                                                                       ('day_period', '=', type),
                                                                       ('calendar_id', '=',
                                                                        employee.resource_calendar_id.id)], limit=1)
        return {
            'hour_from': morning.hour_from,
            'hour_to': morning.hour_to
        }

    @tools.ormcache('stday', 'employee', 'type')
    def get_day_of_week_afternoon(self, stday, employee, type):
        afternoon = employee.resource_calendar_id.attendance_ids.search([('dayofweek', '=', str(stday)),
                                                                         ('day_period', '=', type),
                                                                         ('calendar_id', '=',
                                                                          employee.resource_calendar_id.id)], limit=1)
        return {
            'hour_from': afternoon.hour_from,
            'hour_to': afternoon.hour_to
        }

    @api.constrains('from_time', 'to_time', 'time_custom')
    def _check_from_time_and_to_time(self):
        for holiday in self:
            if holiday.time_custom:
                current_date = holiday.request_date_from
                stday = fields.date.weekday(current_date)
                late_morning = holiday.get_day_of_week_morning(stday, holiday.employee_id, 'morning')
                late_afternoon = holiday.get_day_of_week_afternoon(stday, holiday.employee_id, 'afternoon')
                hour_from = str(float_to_time(late_morning.get('hour_from')).hour)
                minute_from = str(float_to_time(late_morning.get('hour_from')).minute)
                hour_to = str(float_to_time(late_morning.get('hour_to')).hour)
                minute_to = str(float_to_time(late_morning.get('hour_to')).minute)
                if holiday.from_time <= 0.0 or holiday.to_time <= 0.0:
                    raise UserError(_('Hour cannot be equal to 0 or less than 0'))
                elif holiday.from_time > late_morning.get('hour_to') or holiday.from_time < late_morning.get(
                        'hour_from'):
                    raise UserError(_('Morning time must be between %s:%s a.m and %s:%s a.m' % (
                        hour_from, minute_from, hour_to, minute_to)))
                elif holiday.to_time < late_afternoon.get('hour_from') or holiday.to_time > late_afternoon.get(
                        'hour_to'):
                    raise UserError(_('Afternoon time must be between %s:%s p.m and %s:%s p.m' % (
                        hour_from, minute_from, hour_to, minute_to)))

    @api.depends('date_from', 'date_to', 'employee_id', 'from_time', 'to_time', 'time_custom')
    def _compute_number_of_days(self):
        for holiday in self:
            if holiday.date_from and holiday.date_to:
                if not holiday.time_custom:
                    holiday.number_of_days = holiday._get_number_of_days(holiday.date_from, holiday.date_to, holiday.employee_id.id)['days']
                elif holiday.time_custom and holiday.from_time > 0 and holiday.to_time > 0:
                    total_days_off = 0
                    current_date = holiday.request_date_from
                    while current_date <= holiday.request_date_to:
                        stday = fields.date.weekday(current_date)
                        late_morning = holiday.get_day_of_week_morning(stday, holiday.employee_id, 'morning')
                        late_afternoon = holiday.get_day_of_week_afternoon(stday, holiday.employee_id, 'afternoon')
                        time_morning_start = max(holiday.from_time, late_morning.get('hour_from'))
                        if current_date == holiday.request_date_from == holiday.request_date_to:
                            end_time = min(holiday.to_time, late_afternoon.get('hour_to'))
                            if (late_morning.get('hour_from') <= time_morning_start <= late_morning.get(
                                    'hour_to')) and (
                                    end_time <= late_afternoon.get('hour_from')):
                                total_days_off += 0.5
                            elif time_morning_start <= late_morning.get('hour_to') and end_time >= late_afternoon.get(
                                    'hour_to'):
                                total_days_off += 0.5
                            else:
                                total_days_off += 1.0
                        elif current_date == holiday.request_date_from:
                            total_days_off += 0.5
                            if time_morning_start < late_morning.get('hour_to'):
                                total_days_off += 0.5
                        elif current_date == holiday.request_date_to:
                            end_time = min(holiday.to_time, late_afternoon.get('hour_to'))
                            total_days_off += 0.5
                            if end_time > late_afternoon.get('hour_from'):
                                total_days_off += 0.5
                        else:
                            total_days_off += 1.0
                        current_date += timedelta(days=1)
                    holiday.number_of_days = total_days_off
            else:
                holiday.number_of_days = 0

    @api.depends(
        'tz', 'date_from', 'date_to', 'employee_id',
        'holiday_status_id', 'number_of_hours_display',
        'leave_type_request_unit', 'number_of_days', 'mode_company_id',
        'category_id', 'department_id',
    )
    @api.depends_context('short_name', 'hide_employee_name', 'groupby')
    def _compute_display_name(self):
        for leave in self:
            user_tz = timezone(leave.tz)
            date_from_utc = leave.date_from and leave.date_from.astimezone(user_tz).date()
            date_to_utc = leave.date_to and leave.date_to.astimezone(user_tz).date()
            time_off_type_display = leave.holiday_status_id.name
            if self.env.context.get('short_name'):
                short_leave_name = leave.name or time_off_type_display or _('Time Off')
                if leave.leave_type_request_unit == 'hour':
                    leave.display_name = _("%s: %.2f hours", short_leave_name, leave.number_of_hours_display)
                else:
                    leave.display_name = _("%s: %.2f days", short_leave_name, leave.number_of_days)
            else:
                if leave.holiday_type == 'company':
                    target = leave.mode_company_id.name
                elif leave.holiday_type == 'department':
                    target = leave.department_id.name
                elif leave.holiday_type == 'category':
                    target = leave.category_id.name
                elif leave.employee_id:
                    target = leave.employee_id.name
                else:
                    target = ', '.join(leave.sudo().employee_ids.mapped('name'))
                display_date = format_date(self.env, date_from_utc) or ""
                if leave.leave_type_request_unit == 'hour':
                    if self.env.context.get('hide_employee_name') and 'employee_id' in self.env.context.get('group_by',
                                                                                                            []):
                        leave.display_name = _("%(leave_type)s: %(duration).2f hours on %(date)s",
                                               leave_type=time_off_type_display,
                                               duration=leave.number_of_hours_display,
                                               date=display_date,
                                               )
                    elif not time_off_type_display:
                        leave.display_name = _("%(person)s: %(duration).2f hours on %(date)s",
                                               person=target,
                                               duration=leave.number_of_hours_display,
                                               date=display_date,
                                               )
                    else:
                        leave.display_name = _("%(person)s on %(leave_type)s: %(duration).2f hours on %(date)s",
                                               person=target,
                                               leave_type=time_off_type_display,
                                               duration=leave.number_of_hours_display,
                                               date=display_date,
                                               )
                else:
                    if leave.number_of_days > 1 and date_from_utc and date_to_utc:
                        display_date += ' - %s' % format_date(self.env, date_to_utc) or ""
                    if not target or self.env.context.get(
                            'hide_employee_name') and 'employee_id' in self.env.context.get('group_by', []):
                        leave.display_name = _("%(leave_type)s: %(duration).2f days (%(start)s)",
                                               leave_type=time_off_type_display,
                                               duration=leave.number_of_days,
                                               start=display_date,
                                               )
                    elif not time_off_type_display:
                        leave.display_name = _("%(person)s: %(duration).2f days (%(start)s)",
                                               person=target,
                                               duration=leave.number_of_days,
                                               start=display_date,
                                               )
                    else:
                        leave.display_name = _("%(person)s on %(leave_type)s: %(duration).2f days (%(start)s)",
                                               person=target,
                                               leave_type=time_off_type_display,
                                               duration=leave.number_of_days,
                                               start=display_date,
                                               )

    def _check_validity(self):
        sorted_leaves = defaultdict(lambda: self.env['hr.leave'])
        for leave in self:
            sorted_leaves[(leave.holiday_status_id, leave.date_from.date())] |= leave
        for (leave_type, date_from), leaves in sorted_leaves.items():
            if leave_type.requires_allocation == 'no':
                continue
            employees = self.env['hr.employee']
            for leave in leaves:
                employees |= leave._get_employees_from_holiday_type()
            leave_data = leave_type.get_allocation_data(employees, date_from)
            if leave_type.allows_negative:
                max_excess = leave_type.max_allowed_negative
                for employee in employees:
                    if leave_data[employee] and leave_data[employee][0][1]['virtual_remaining_leaves'] < -max_excess:
                        raise ValidationError(_("There is no valid allocation to cover that request."))
                continue

            previous_leave_data = leave_type.with_context(
                ignored_leave_ids=leaves.ids
            ).get_allocation_data(employees, date_from)
            for employee in employees:
                previous_emp_data = previous_leave_data[employee] and previous_leave_data[employee][0][1][
                    'virtual_excess_data']
                emp_data = leave_data[employee] and leave_data[employee][0][1]['virtual_excess_data']
                if not previous_emp_data and not emp_data:
                    continue
                if previous_emp_data != emp_data and len(emp_data) >= len(previous_emp_data):
                    raise ValidationError(_("There is no valid allocation to cover that request."))

    @api.constrains('date_from', 'date_to', 'employee_id')
    def _check_date(self):
        if self.env.context.get('leave_skip_date_check', False):
            return

        all_employees = self.all_employee_ids
        all_leaves = self.search([
            ('date_from', '<', max(self.mapped('date_to'))),
            ('date_to', '>', min(self.mapped('date_from'))),
            ('employee_id', 'in', all_employees.ids),
            ('id', 'not in', self.ids),
            ('state', 'not in', ['cancel', 'refuse']),
        ])
        for holiday in self:
            domain = [
                ('date_from', '<', holiday.date_to),
                ('date_to', '>', holiday.date_from),
                ('id', '!=', holiday.id),
                ('state', 'not in', ['cancel', 'refuse']),
            ]

            employee_ids = (holiday.employee_id | holiday.sudo().employee_ids).ids
            search_domain = domain + [('employee_id', 'in', employee_ids)]
            conflicting_holidays = all_leaves.filtered_domain(search_domain)

            if conflicting_holidays:
                conflicting_holidays_list = []
                # Do not display the name of the employee if the conflicting holidays have an employee_id.user_id equivalent to the user id
                holidays_only_have_uid = bool(holiday.employee_id)
                holiday_states = dict(conflicting_holidays.fields_get(allfields=['state'])['state']['selection'])
                for conflicting_holiday in conflicting_holidays:
                    conflicting_holiday_data = {}
                    conflicting_holiday_data['employee_name'] = conflicting_holiday.employee_id.name
                    conflicting_holiday_data['date_from'] = format_date(self.env,
                                                                        min(conflicting_holiday.mapped('date_from')))
                    conflicting_holiday_data['date_to'] = format_date(self.env,
                                                                      min(conflicting_holiday.mapped('date_to')))
                    conflicting_holiday_data['state'] = holiday_states[conflicting_holiday.state]
                    if conflicting_holiday.employee_id.user_id.id != self.env.uid:
                        holidays_only_have_uid = False
                    if conflicting_holiday_data not in conflicting_holidays_list:
                        conflicting_holidays_list.append(conflicting_holiday_data)
                if not conflicting_holidays_list:
                    return
                conflicting_holidays_strings = []
                if holidays_only_have_uid:
                    for conflicting_holiday_data in conflicting_holidays_list:
                        conflicting_holidays_string = _('from %(date_from)s to %(date_to)s - %(state)s',
                                                        date_from=conflicting_holiday_data['date_from'],
                                                        date_to=conflicting_holiday_data['date_to'],
                                                        state=conflicting_holiday_data['state'])
                        conflicting_holidays_strings.append(conflicting_holidays_string)
                    raise ValidationError(_("""\
    You've already booked time off which overlaps with this period:
    %s
    Attempting to double-book your time off won't magically make your vacation 2x better!
    """,
                                            "\n".join(conflicting_holidays_strings)))
                for conflicting_holiday_data in conflicting_holidays_list:
                    conflicting_holidays_string = "\n" + _(
                        '%(employee_name)s - from %(date_from)s to %(date_to)s - %(state)s',
                        employee_name=conflicting_holiday_data['employee_name'],
                        date_from=conflicting_holiday_data['date_from'],
                        date_to=conflicting_holiday_data['date_to'],
                        state=conflicting_holiday_data['state'])
                    conflicting_holidays_strings.append(conflicting_holidays_string)
                raise ValidationError(_(
                    "An employee already booked time off which overlaps with this period:%s",
                    "".join(conflicting_holidays_strings)))

    @api.depends('resource_calendar_id.tz')
    def _compute_tz(self):
        for leave in self:
            leave.tz = leave.resource_calendar_id.tz or self.env.company.resource_calendar_id.tz or self.env.user.tz or 'UTC'

    @api.depends('number_of_hours')
    def _compute_number_of_hours_display(self):
        for leave in self:
            leave.number_of_hours_display = leave.number_of_hours

    @api.depends('employee_company_id', 'mode_company_id')
    def _compute_company_id(self):
        for holiday in self:
            holiday.company_id = holiday.employee_company_id \
                                 or holiday.mode_company_id \
                                 or holiday.department_id.company_id \
                                 or self.env.company

    def _get_duration(self, check_leave_type=True, resource_calendar=None):
        """
        This method is factored out into a separate method from
        _compute_duration so it can be hooked and called without necessarily
        modifying the fields and triggering more computes of fields that
        depend on number_of_hours or number_of_days.
        """
        self.ensure_one()
        resource_calendar = resource_calendar or self.resource_calendar_id

        if not self.date_from or not self.date_to or not resource_calendar:
            return (0, 0)
        hours, days = (0, 0)
        if self.employee_id:
            # We force the company in the domain as we are more than likely in a compute_sudo
            domain = [('time_type', '=', 'leave'),
                      ('company_id', 'in', self.env.companies.ids + self.env.context.get('allowed_company_ids', [])),
                      # When searching for resource leave intervals, we exclude the one that
                      # is related to the leave we're currently trying to compute for.
                      '|', ('holiday_id', '=', False), ('holiday_id', '!=', self.id)]
            if self.leave_type_request_unit == 'day' and check_leave_type:
                # list of tuples (day, hours)
                work_time_per_day_list = self.employee_id.list_work_time_per_day(self.date_from, self.date_to,
                                                                                 calendar=resource_calendar,
                                                                                 domain=domain)
                days = len(work_time_per_day_list)
                hours = sum(map(lambda t: t[1], work_time_per_day_list))
            else:
                work_days_data = self.employee_id._get_work_days_data_batch(self.date_from, self.date_to, domain=domain,
                                                                            calendar=resource_calendar)[
                    self.employee_id.id]
                hours, days = work_days_data['hours'], work_days_data['days']
        else:
            today_hours = resource_calendar.get_work_hours_count(
                datetime.combine(self.date_from.date(), time.min),
                datetime.combine(self.date_from.date(), time.max),
                False)
            hours = resource_calendar.get_work_hours_count(self.date_from, self.date_to)
            days = hours / (today_hours or HOURS_PER_DAY)
        if self.leave_type_request_unit == 'day' and check_leave_type:
            days = ceil(days)
        return (days, hours)

    @api.depends_context('uid')
    @api.depends('employee_id')
    def _compute_is_user_only_responsible(self):
        user = self.env.user
        self.is_user_only_responsible = user.has_group('hr_holidays.group_hr_holidays_responsible') \
                                        and not user.has_group('hr_holidays.group_hr_holidays_user')

    def _get_employee_domain(self):
        domain = [
            ('active', '=', True),
            ('company_id', 'in', self.env.companies.ids),
        ]
        if not self.env.user.has_group('hr_holidays.group_hr_holidays_user'):
            domain += [
                '|',
                ('user_id', '=', self.env.uid),
                ('leave_manager_id', '=', self.env.uid),
            ]
        return domain

    @api.depends('employee_id', 'employee_ids')
    def _compute_from_employee_id(self):
        for holiday in self:
            holiday.manager_id = holiday.employee_id.parent_id.id
            if holiday.holiday_status_id.requires_allocation == 'no':
                continue
            if not holiday.employee_id or len(holiday.sudo().employee_ids) > 1:
                holiday.holiday_status_id = False
            elif holiday.employee_id.user_id != self.env.user and holiday._origin.employee_id != holiday.employee_id:
                if holiday.employee_id and not holiday.holiday_status_id.with_context(
                        employee_id=holiday.employee_id.id).has_valid_allocation:
                    holiday.holiday_status_id = False

    @api.depends('request_date_from_period', 'request_hour_from', 'request_hour_to', 'request_date_from',
                 'request_date_to',
                 'request_unit_half', 'request_unit_hours', 'employee_id')
    def _compute_date_from_to(self):
        for holiday in self:
            if not holiday.request_date_from:
                holiday.date_from = False
            elif not holiday.request_unit_half and not holiday.request_unit_hours and not holiday.request_date_to:
                holiday.date_to = False
            else:
                if (
                        holiday.request_unit_half or holiday.request_unit_hours) and holiday.request_date_to != holiday.request_date_from:
                    holiday.request_date_to = holiday.request_date_from
                day_period = {
                    'am': 'morning',
                    'pm': 'afternoon'
                }.get(holiday.request_date_from_period, None) if holiday.request_unit_half else None

                attendance_from, attendance_to = holiday._get_attendances_custom(holiday.request_date_from,
                                                                                 holiday.request_date_to,
                                                                                 day_period=day_period)

                compensated_request_date_from = holiday.request_date_from
                compensated_request_date_to = holiday.request_date_to

                if holiday.request_unit_hours:
                    hour_from = holiday.request_hour_from
                    hour_to = holiday.request_hour_to
                else:
                    hour_from = attendance_from.hour_from
                    hour_to = attendance_to.hour_to

                holiday.date_from = self._to_utc(compensated_request_date_from, hour_from,
                                                 holiday.employee_id or holiday)
                holiday.date_to = self._to_utc(compensated_request_date_to, hour_to, holiday.employee_id or holiday)

    @api.depends('holiday_type', 'employee_id', 'department_id', 'mode_company_id')
    def _compute_resource_calendar_id(self):
        for leave in self:
            calendar = False
            if leave.holiday_type == 'employee':
                calendar = leave.employee_id.resource_calendar_id
                # YTI: Crappy hack: Move this to a new dedicated hr_holidays_contract module
                # We use the request dates to find the contracts, because date_from
                # and date_to are not set yet at this point. Since these dates are
                # used to get the contracts for which these leaves apply and
                # contract start- and end-dates are just dates (and not datetimes)
                # these dates are comparable.
                if 'hr.contract' in self.env and leave.employee_id:
                    contracts = self.env['hr.contract'].search([
                        '|', ('state', 'in', ['open', 'close']),
                        '&', ('state', '=', 'draft'),
                        ('kanban_state', '=', 'done'),
                        ('employee_id', '=', leave.employee_id.id),
                        ('date_start', '<=', leave.request_date_to),
                        '|', ('date_end', '=', False),
                        ('date_end', '>=', leave.request_date_from),
                    ])
                    if contracts:
                        # If there are more than one contract they should all have the
                        # same calendar, otherwise a constraint is violated.
                        calendar = contracts[:1].resource_calendar_id
            elif leave.holiday_type == 'department':
                calendar = leave.department_id.company_id.resource_calendar_id
            elif leave.holiday_type == 'company':
                calendar = leave.mode_company_id.resource_calendar_id
            leave.resource_calendar_id = calendar or self.env.company.resource_calendar_id

    @api.depends('leave_type_request_unit', 'number_of_days')
    def _compute_leave_type_increases_duration(self):
        for holiday in self:
            days = holiday._get_duration(check_leave_type=False)[0]
            holiday.leave_type_increases_duration = holiday.leave_type_request_unit == 'day' and days < holiday.number_of_days

    @api.depends('date_from', 'date_to', 'resource_calendar_id', 'holiday_status_id.request_unit')
    def _compute_duration(self):
        for holiday in self:
            days, hours = holiday._get_duration()
            holiday.number_of_hours = hours
            holiday.number_of_days = days

    @api.depends('number_of_days')
    def _compute_last_several_days(self):
        for holiday in self:
            holiday.last_several_days = holiday.number_of_days > 1

    @api.model_create_multi
    def create(self, vals_list):
        employee_ids = []
        for values in vals_list:
            if values.get('employee_id'):
                employee_ids.append(values['employee_id'])
        employees = self.env['hr.employee'].browse(employee_ids)

        """ Override to avoid automatic logging of creation """
        if not self._context.get('leave_fast_create'):
            leave_types = self.env['hr.leave.type'].browse(
                [values.get('holiday_status_id') for values in vals_list if values.get('holiday_status_id')])
            mapped_validation_type = {leave_type.id: leave_type.leave_validation_type for leave_type in leave_types}

            for values in vals_list:
                employee_id = values.get('employee_id', False)
                leave_type_id = values.get('holiday_status_id')
                # Handle automatic department_id
                if not values.get('department_id'):
                    values.update(
                        {'department_id': employees.filtered(lambda emp: emp.id == employee_id).department_id.id})

                # Handle no_validation
                if mapped_validation_type[leave_type_id] == 'no_validation':
                    values.update({'state': 'confirm'})

                if 'state' not in values:
                    # To mimic the behavior of compute_state that was always triggered, as the field was readonly
                    values['state'] = 'confirm' if mapped_validation_type[leave_type_id] != 'no_validation' else 'draft'

                # Handle double validation
                if mapped_validation_type[leave_type_id] == 'both':
                    self._check_double_validation_rules(employee_id, values.get('state', False))

        holidays = super(HolidaysRequest, self.with_context(mail_create_nosubscribe=True)).create(vals_list)
        holidays._check_validity()
        today = datetime.today()
        for holiday in holidays:
            if holiday.holiday_status_id.requires_allocation == 'yes' and holiday.holiday_status_id.allows_negative:
                if holiday.holiday_status_id.time_application == 'in_month':
                    if holiday.date_from.month != today.month and holiday.date_to.month != today.month:
                        raise ValidationError("The time must be within the current month")
                else:
                    if holiday.date_from.month == today.month and holiday.date_to.month == today.month:
                        raise ValidationError("The time must be within the next month")
            if not self._context.get('leave_fast_create'):
                # Everything that is done here must be done using sudo because we might
                # have different create and write rights
                # eg : holidays_user can create a leave request with validation_type = 'manager' for someone else
                # but they can only write on it if they are leave_manager_id
                holiday_sudo = holiday.sudo()
                holiday_sudo.add_follower(employee_id)
                if holiday.validation_type == 'manager':
                    holiday_sudo.message_subscribe(partner_ids=holiday.employee_id.leave_manager_id.partner_id.ids)
                if holiday.validation_type == 'no_validation':
                    # Automatic validation should be done in sudo, because user might not have the rights to do it by himself
                    holiday_sudo.action_validate()
                    holiday_sudo.message_subscribe(partner_ids=holiday._get_responsible_for_approval().partner_id.ids)
                    holiday_sudo.message_post(body=_("The time off has been automatically approved"),
                                              subtype_xmlid="mail.mt_comment")  # Message from OdooBot (sudo)
                elif not self._context.get('import_file'):
                    holiday_sudo.activity_update()
        return holidays

    def write(self, values):
        if 'active' in values and not self.env.context.get('from_cancel_wizard'):
            raise UserError(_("You can't manually archive/unarchive a time off."))

        is_officer = self.env.user.has_group('hr_holidays.group_hr_holidays_user') or self.env.is_superuser()
        if not is_officer and values.keys() - {'attachment_ids', 'supported_attachment_ids',
                                               'message_main_attachment_id'}:
            if any(hol.date_from.date() < fields.Date.today() and hol.employee_id.leave_manager_id != self.env.user for
                   hol in self):
                raise UserError(_('You must have manager rights to modify/validate a time off that already begun'))

        # Unlink existing resource.calendar.leaves for validated time off
        if 'state' in values and values['state'] != 'validate':
            validated_leaves = self.filtered(lambda l: l.state == 'validate')
            validated_leaves._remove_resource_leave()

        employee_id = values.get('employee_id', False)
        if not self.env.context.get('leave_fast_create'):
            if values.get('state'):
                self._check_approval_update(values['state'])
                if any(holiday.validation_type == 'both' for holiday in self):
                    if values.get('employee_id'):
                        employees = self.env['hr.employee'].browse(values.get('employee_id'))
                    else:
                        employees = self.mapped('employee_id')
                    self._check_double_validation_rules(employees, values['state'])
            if 'date_from' in values:
                values['request_date_from'] = values['date_from']
            if 'date_to' in values:
                values['request_date_to'] = values['date_to']
        result = super(HolidaysRequest, self).write(values)
        if any(field in values for field in
               ['request_date_from', 'date_from', 'request_date_from', 'date_to', 'holiday_status_id', 'employee_id']):
            self._check_validity()
        if not self.env.context.get('leave_fast_create'):
            for holiday in self:
                if employee_id:
                    holiday.add_follower(employee_id)

        return result

    @api.ondelete(at_uninstall=False)
    def _unlink_if_correct_states(self):
        error_message = _('You cannot delete a time off which is in %s state')
        state_description_values = {elem[0]: elem[1] for elem in self._fields['state']._description_selection(self.env)}
        if not self.user_has_groups('hr_holidays.group_hr_holidays_user'):
            for hol in self:
                if hol.state not in ['draft', 'confirm']:
                    raise UserError(error_message % state_description_values.get(self[:1].state))
                if hol.sudo().employee_ids and not hol.employee_id:
                    raise UserError(_('You cannot delete a time off assigned to several employees'))
        else:
            for holiday in self.filtered(lambda holiday: holiday.state not in ['draft', 'cancel', 'confirm']):
                raise UserError(error_message % (state_description_values.get(holiday.state),))

    @api.depends_context('uid')
    def _compute_description(self):
        for leave in self:
            if leave.employee_company_id.id == self.env.ref('base.main_company').id:
                leave.name = leave.sudo().private_name
            else:
                super(HolidaysRequest, self)._compute_description()

    @api.depends_context('uid')
    @api.depends('employee_id')
    def _compute_is_user_only_responsible(self):
        user = self.env.user
        self.is_user_only_responsible = user.has_group('hr_holidays.group_hr_holidays_responsible') \
                                        and not user.has_group('hr_holidays.group_hr_holidays_user')

    def unlink(self):
        self._force_cancel(_("deleted by %s (uid=%d).",
                             self.env.user.display_name, self.env.user.id
                             ))
        return super(HolidaysRequest, self.with_context(leave_skip_date_check=True)).unlink()

    def copy_data(self, default=None):
        if default and 'request_date_from' in default and 'request_date_to' in default:
            return super().copy_data(default)
        elif self.state in {"cancel", "refuse"}:  # No overlap constraint in these cases
            return super().copy_data(default)
        raise UserError(_('A time off cannot be duplicated.'))

    @api.model
    def action_open_records(self, leave_ids):
        if len(leave_ids) == 1:
            return {
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_id': leave_ids[0],
                'res_model': 'hr.leave',
            }
        return {
            'type': 'ir.actions.act_window',
            'view_mode': [[False, 'tree'], [False, 'form']],
            'domain': [('id', 'in', leave_ids.ids)],
            'res_model': 'hr.leave',
        }

    def _prepare_resource_leave_vals(self):
        """Hook method for others to inject data
        """
        self.ensure_one()
        return {
            'name': _("%s: Time Off", self.employee_id.name),
            'date_from': self.date_from,
            'holiday_id': self.id,
            'date_to': self.date_to,
            'resource_id': self.employee_id.resource_id.id,
            'calendar_id': self.resource_calendar_id.id,
            'time_type': self.holiday_status_id.time_type,
        }

    def _create_resource_leave(self):
        """ This method will create entry in resource calendar time off object at the time of holidays validated
        :returns: created `resource.calendar.leaves`
        """
        vals_list = [leave._prepare_resource_leave_vals() for leave in self]
        return self.env['resource.calendar.leaves'].sudo().create(vals_list)

    def _prepare_holidays_meeting_values(self):
        result = defaultdict(list)
        for holiday in self:
            user = holiday.user_id
            if holiday.leave_type_request_unit == 'hour':
                meeting_name = _("%s on Time Off : %.2f hour(s)") % (
                holiday.employee_id.name or holiday.category_id.name, holiday.number_of_hours_display)
                allday_value = float_compare(holiday.number_of_days, 1.0, 1) >= 0
            else:
                meeting_name = _("%s on Time Off : %.2f day(s)") % (
                holiday.employee_id.name or holiday.category_id.name, holiday.number_of_days)
                allday_value = not holiday.request_unit_half
            meeting_values = {
                'name': meeting_name,
                'duration': holiday.number_of_days * (holiday.resource_calendar_id.hours_per_day or HOURS_PER_DAY),
                'description': holiday.notes,
                'user_id': user.id,
                'start': holiday.date_from,
                'stop': holiday.date_to,
                'allday': allday_value,
                'privacy': 'confidential',
                'event_tz': user.tz,
                'activity_ids': [(5, 0, 0)],
                'res_id': holiday.id,
            }
            # Add the partner_id (if exist) as an attendee
            partner_id = (user and user.partner_id) or (holiday.employee_id and holiday.employee_id.work_contact_id)
            if partner_id:
                meeting_values['partner_ids'] = [(4, partner_id.id)]
            result[user.id].append(meeting_values)
        return result

    def action_approve(self, check_state=True):
        # if validation_type == 'both': this method is the first approval approval
        # if validation_type != 'both': this method calls action_validate() below

        # Do not check the state in case we are redirected from the dashboard
        if check_state and any(holiday.state != 'confirm' for holiday in self):
            raise UserError(_('Time off request must be confirmed ("To Approve") in order to approve it.'))

        current_employee = self.env.user.employee_id
        self.filtered(lambda hol: hol.validation_type == 'both').write(
            {'state': 'validate1', 'first_approver_id': current_employee.id})

        # Post a second message, more verbose than the tracking message
        for holiday in self.filtered(lambda holiday: holiday.employee_id.user_id):
            user_tz = timezone(holiday.tz)
            utc_tz = pytz.utc.localize(holiday.date_from).astimezone(user_tz)
            # Do not notify the employee by mail, in case if the time off still needs Officer's approval
            notify_partner_ids = holiday.employee_id.user_id.partner_id.ids if holiday.validation_type != 'both' else []
            holiday.message_post(
                body=_(
                    'Your %(leave_type)s planned on %(date)s has been accepted',
                    leave_type=holiday.holiday_status_id.display_name,
                    date=utc_tz.replace(tzinfo=None)
                ),
                partner_ids=notify_partner_ids)

        self.filtered(lambda hol: not hol.validation_type == 'both').action_validate()
        if not self.env.context.get('leave_fast_create'):
            self.activity_update()
        return True

    def _split_leaves(self, split_date_from, split_date_to):
        """
        Split leaves on the given full-day interval. The leaves will be split
        into two new leaves: the period up until (but not including)
        split_date_from and the period starting at (and including)
        split_date_to.

        This means that the period in between split_date_from and split_date_to
        will no longer be covered by the new leaves. In order to split a leave
        without losing any leave coverage, split_date_from and split_date_to
        should therefore be the same.

        Another important note to make is that this method only splits leaves
        on full-day intervals. Logic to split leaves on partial days or hours
        is not straightforward as you have to take into account working hours
        and timezones. It's also not clear that we would want to handle this
        automatically. The method will therefore also only work on leaves that
        are taken in full or half days (Though a half day leave in the interval
        will simply be refused - there are no multi-day spanning half-day
        leaves)

        The method creates one or two new leaves per leave that needs to be
        split and refuses the original leave.
        """
        # Keep track of the original states before refusing the leaves and creating new ones
        original_states = {l.id: l.state for l in self}

        # Refuse all original leaves
        self.action_refuse()
        split_leaves_vals = []

        # Only leaves that span a period outside of the split interval need
        # to be split.
        multi_day_leaves = self.filtered(
            lambda l: l.request_date_from < split_date_from or l.request_date_to >= split_date_to)

        for leave in multi_day_leaves:
            # Leaves in days
            new_leave_vals = []

            # Get the values to create the leave before the split
            if leave.request_date_from < split_date_from:
                new_leave_vals.append(leave.copy_data({
                    'request_date_from': leave.request_date_from,
                    'request_date_to': split_date_from + timedelta(days=-1),
                    'state': original_states[leave.id],
                })[0])

            # Do the same for the new leave after the split
            if leave.request_date_to >= split_date_to:
                new_leave_vals.append(leave.copy_data({
                    'request_date_from': split_date_to,
                    'request_date_to': leave.request_date_to,
                    'state': original_states[leave.id],
                })[0])

            # For those two new leaves, only create them if they actually
            # have a non-zero duration.
            for leave_vals in new_leave_vals:
                new_leave = self.env['hr.leave'].new(leave_vals)
                new_leave._compute_date_from_to()
                # Could happen for part-time contract, that time off is not necessary
                # anymore.
                # Imagine you work on monday-wednesday-friday only.
                # You take a time off on friday.
                # We create a company time off on friday.
                # By looking at the last attendance before the company time off
                # start date to compute the date_to, you would have a date_from > date_to.
                # Just don't create the leave at that time. That's the reason why we use
                # new instead of create. As the leave is not actually created yet, the sql
                # constraint didn't check date_from < date_to yet.
                if new_leave.date_from < new_leave.date_to:
                    split_leaves_vals.append(new_leave._convert_to_write(new_leave._cache))

        split_leaves = self.env['hr.leave'].with_context(
            tracking_disable=True,
            mail_activity_automation_skip=True,
            leave_fast_create=True,
            leave_skip_state_check=True
        ).create(split_leaves_vals)

        split_leaves.filtered(lambda l: l.state in 'validate')._validate_leave_request()

    def action_validate(self):
        current_employee = self.env.user.employee_id
        leaves = self._get_leaves_on_public_holiday()
        if leaves:
            raise ValidationError(
                _('The following employees are not supposed to work during that period:\n %s') % ','.join(
                    leaves.mapped('employee_id.name')))

        if any(holiday.state not in ['confirm', 'validate1'] and holiday.validation_type != 'no_validation' for holiday
               in self):
            raise UserError(_('Time off request must be confirmed in order to approve it.'))

        self.write({'state': 'validate'})

        leaves_second_approver = self.env['hr.leave']
        leaves_first_approver = self.env['hr.leave']

        for leave in self:
            if leave.validation_type == 'both':
                leaves_second_approver += leave
            else:
                leaves_first_approver += leave

            if leave.holiday_type != 'employee' or \
                    (leave.holiday_type == 'employee' and len(leave.sudo().employee_ids) > 1):
                employees = leave._get_employees_from_holiday_type()

                conflicting_leaves = self.env['hr.leave'].with_context(
                    tracking_disable=True,
                    mail_activity_automation_skip=True,
                    leave_fast_create=True
                ).search([
                    ('date_from', '<=', leave.date_to),
                    ('date_to', '>', leave.date_from),
                    ('state', 'not in', ['cancel', 'refuse']),
                    ('holiday_type', '=', 'employee'),
                    ('employee_id', 'in', employees.ids)])

                if conflicting_leaves:
                    # YTI: More complex use cases could be managed in master
                    if leave.leave_type_request_unit != 'day' or any(
                            l.leave_type_request_unit == 'hour' for l in conflicting_leaves):
                        raise ValidationError(_('You can not have 2 time off that overlaps on the same day.'))

                    conflicting_leaves._split_leaves(leave.request_date_from, leave.request_date_to + timedelta(days=1))

                values = leave._prepare_employees_holiday_values(employees)
                leaves = self.env['hr.leave'].with_context(
                    tracking_disable=True,
                    mail_activity_automation_skip=True,
                    leave_fast_create=True,
                    no_calendar_sync=True,
                    leave_skip_state_check=True,
                    # date_from and date_to are computed based on the employee tz
                    # If _compute_date_from_to is used instead, it will trigger _compute_number_of_days
                    # and create a conflict on the number of days calculation between the different leaves
                    leave_compute_date_from_to=True,
                ).create(values)

                leaves._validate_leave_request()

        leaves_second_approver.write({'second_approver_id': current_employee.id})
        leaves_first_approver.write({'first_approver_id': current_employee.id})

        employee_requests = self.filtered(lambda hol: hol.holiday_type == 'employee')
        employee_requests._validate_leave_request()
        if not self.env.context.get('leave_fast_create'):
            employee_requests.filtered(lambda holiday: holiday.validation_type != 'no_validation').activity_update()
        return True

    def action_refuse(self):
        current_employee = self.env.user.employee_id
        if any(holiday.state not in ['draft', 'confirm', 'validate', 'validate1'] for holiday in self):
            raise UserError(_('Time off request must be confirmed or validated in order to refuse it.'))

        self._notify_manager()
        validated_holidays = self.filtered(lambda hol: hol.state == 'validate1')
        validated_holidays.write({'state': 'refuse', 'first_approver_id': current_employee.id})
        (self - validated_holidays).write({'state': 'refuse', 'second_approver_id': current_employee.id})
        # Delete the meeting
        self.mapped('meeting_id').write({'active': False})
        # If a category that created several holidays, cancel all related
        linked_requests = self.mapped('linked_request_ids')
        if linked_requests:
            linked_requests.action_refuse()

        # Post a second message, more verbose than the tracking message
        for holiday in self:
            if holiday.employee_id.user_id:
                holiday.message_post(
                    body=_('Your %(leave_type)s planned on %(date)s has been refused',
                           leave_type=holiday.holiday_status_id.display_name, date=holiday.date_from),
                    partner_ids=holiday.employee_id.user_id.partner_id.ids)

        self.activity_update()
        return True

    def _get_employees_from_holiday_type(self):
        self.ensure_one()
        if self.holiday_type == 'employee':
            employees = self.sudo().employee_ids
        elif self.holiday_type == 'category':
            employees = self.category_id.employee_ids
        elif self.holiday_type == 'company':
            employees = self.env['hr.employee'].search([('company_id', '=', self.mode_company_id.id)])
        else:
            employees = self.department_id.member_ids
        return employees

    def _notify_manager(self):
        leaves = self.filtered(
            lambda hol: (hol.validation_type == 'both' and hol.state in ['validate1', 'validate']) or (
                        hol.validation_type == 'manager' and hol.state == 'validate'))
        for holiday in leaves:
            responsible = holiday.employee_id.leave_manager_id.partner_id.ids
            if responsible:
                self.env['mail.thread'].sudo().message_notify(
                    partner_ids=responsible,
                    model_description='Time Off',
                    subject=_('Refused Time Off'),
                    body=_(
                        '%(holiday_name)s has been refused.',
                        holiday_name=holiday.display_name,
                    ),
                    email_layout_xmlid='mail.mail_notification_light',
                )

    def _action_user_cancel(self, reason):
        self.ensure_one()
        if not self.can_cancel:
            raise ValidationError(_('This time off cannot be canceled.'))

        self._force_cancel(reason, 'mail.mt_note')

    def _force_cancel(self, reason, msg_subtype='mail.mt_comment'):
        recs = self.browse() if self.env.context.get(MODULE_UNINSTALL_FLAG) else self
        for leave in recs:
            leave.message_post(
                body=_('The time off has been canceled: %s', reason),
                subtype_xmlid=msg_subtype
            )

            responsibles = self.env['res.partner']
            # manager
            if (leave.holiday_status_id.leave_validation_type == 'manager' and leave.state == 'validate') or (
                    leave.holiday_status_id.leave_validation_type == 'both' and leave.state == 'validate1'):
                responsibles = leave.employee_id.leave_manager_id.partner_id
            # officer
            elif leave.holiday_status_id.leave_validation_type == 'hr' and leave.state == 'validate':
                responsibles = leave.holiday_status_id.responsible_ids.partner_id
            # both
            elif leave.holiday_status_id.leave_validation_type == 'both' and leave.state == 'validate':
                responsibles = leave.employee_id.leave_manager_id.partner_id
                responsibles |= leave.holiday_status_id.responsible_ids.partner_id

            if responsibles:
                self.env['mail.thread'].sudo().message_notify(
                    partner_ids=responsibles.ids,
                    model_description='Time Off',
                    subject=_('Canceled Time Off'),
                    body=_(
                        "%(leave_name)s has been cancelled with the justification: <br/> %(reason)s.",
                        leave_name=leave.display_name,
                        reason=reason
                    ),
                    email_layout_xmlid='mail.mail_notification_light',
                )
        leave_sudo = self.sudo()
        leave_sudo.with_context(from_cancel_wizard=True).active = False
        leave_sudo.meeting_id.active = False
        leave_sudo._remove_resource_leave()

    def action_documents(self):
        domain = [('id', 'in', self.attachment_ids.ids)]
        return {
            'name': _("Supporting Documents"),
            'type': 'ir.actions.act_window',
            'res_model': 'ir.attachment',
            'context': {'create': False},
            'view_mode': 'kanban',
            'domain': domain
        }

    def _check_approval_update(self, state):
        """ Check if target state is achievable. """
        if self.env.is_superuser():
            return

        current_employee = self.env.user.employee_id
        is_officer = self.env.user.has_group('hr_holidays.group_hr_holidays_user')
        is_manager = self.env.user.has_group('hr_holidays.group_hr_holidays_manager')

        for holiday in self:
            val_type = holiday.validation_type

            if not is_manager and state != 'confirm':
                if state == 'draft':
                    if holiday.state == 'refuse':
                        raise UserError(_('Only a Time Off Manager can reset a refused leave.'))
                    if holiday.date_from and holiday.date_from.date() <= fields.Date.today():
                        raise UserError(_('Only a Time Off Manager can reset a started leave.'))
                    if holiday.employee_id != current_employee:
                        raise UserError(_('Only a Time Off Manager can reset other people leaves.'))
                else:
                    if val_type == 'no_validation' and current_employee == holiday.employee_id:
                        continue
                    # use ir.rule based first access check: department, members, ... (see security.xml)
                    holiday.check_access_rule('write')

                    # This handles states validate1 validate and refuse
                    if holiday.employee_id == current_employee \
                            and self.env.user != holiday.employee_id.leave_manager_id \
                            and not is_officer:
                        raise UserError(_('Only a Time Off Officer or Manager can approve/refuse its own requests.'))

                    if (state == 'validate1' and val_type == 'both') and holiday.holiday_type == 'employee':
                        if not is_officer and self.env.user != holiday.employee_id.leave_manager_id:
                            raise UserError(
                                _('You must be either %s\'s manager or Time off Manager to approve this leave') % (
                                    holiday.employee_id.name))

                    if (state == 'validate' and val_type == 'manager') \
                            and self.env.user != (holiday.employee_id | holiday.sudo().employee_ids).leave_manager_id \
                            and not is_officer:
                        if holiday.employee_id:
                            employees = holiday.employee_id
                        else:
                            employees = ', '.join(
                                holiday.sudo().employee_ids.filtered(lambda e: e.leave_manager_id != self.env.user).mapped(
                                    'name'))
                        raise UserError(_('You must be %s\'s Manager to approve this leave', employees))

                    if not is_officer and (
                            state == 'validate' and val_type == 'hr') and holiday.holiday_type == 'employee':
                        raise UserError(
                            _('You must either be a Time off Officer or Time off Manager to approve this leave'))

    # ------------------------------------------------------------
    # Activity methods
    # ------------------------------------------------------------

    def _get_responsible_for_approval(self):
        self.ensure_one()

        responsible = self.env.user

        if self.holiday_type != 'employee':
            return responsible

        if self.validation_type == 'manager' or (self.validation_type == 'both' and self.state == 'confirm'):
            if self.employee_id.leave_manager_id:
                responsible = self.employee_id.leave_manager_id
            elif self.employee_id.parent_id.user_id:
                responsible = self.employee_id.parent_id.user_id
        elif self.validation_type == 'hr' or (self.validation_type == 'both' and self.state == 'validate1'):
            if self.holiday_status_id.responsible_ids:
                responsible = self.holiday_status_id.responsible_ids

        return responsible

    def activity_update(self):
        to_clean, to_do, to_do_confirm_activity = self.env['hr.leave'], self.env['hr.leave'], self.env['hr.leave']
        activity_vals = []
        today = fields.Date.today()
        model_id = self.env.ref('hr_holidays.model_hr_leave').id
        confirm_activity = self.env.ref('hr_holidays.mail_act_leave_approval')
        approval_activity = self.env.ref('hr_holidays.mail_act_leave_second_approval')
        for holiday in self:
            if holiday.state == 'draft':
                to_clean |= holiday
            elif holiday.state in ['confirm', 'validate1']:
                if holiday.holiday_status_id.leave_validation_type != 'no_validation':
                    if holiday.state == 'confirm':
                        activity_type = confirm_activity
                        note = _(
                            'New %(leave_type)s Request created by %(user)s',
                            leave_type=holiday.holiday_status_id.name,
                            user=holiday.create_uid.name,
                        )
                    else:
                        activity_type = approval_activity
                        note = _(
                            'Second approval request for %(leave_type)s',
                            leave_type=holiday.holiday_status_id.name,
                        )
                        to_do_confirm_activity |= holiday
                    user_ids = holiday.sudo()._get_responsible_for_approval().ids or self.env.user.ids
                    for user_id in user_ids:
                        date_deadline = (
                            (holiday.date_from -
                             relativedelta(**{activity_type.delay_unit: activity_type.delay_count or 0})).date()
                            if holiday.date_from else today)
                        if date_deadline < today:
                            date_deadline = today
                        activity_vals.append({
                            'activity_type_id': activity_type.id,
                            'automated': True,
                            'date_deadline': date_deadline,
                            'note': note,
                            'user_id': user_id,
                            'res_id': holiday.id,
                            'res_model_id': model_id,
                        })
            elif holiday.state == 'validate':
                to_do |= holiday
            elif holiday.state == 'refuse':
                to_clean |= holiday
        if to_clean:
            to_clean.activity_unlink(
                ['hr_holidays.mail_act_leave_approval', 'hr_holidays.mail_act_leave_second_approval'])
        if to_do_confirm_activity:
            to_do_confirm_activity.activity_feedback(['hr_holidays.mail_act_leave_approval'])
        if to_do:
            to_do.activity_feedback(
                ['hr_holidays.mail_act_leave_approval', 'hr_holidays.mail_act_leave_second_approval'])
        self.env['mail.activity'].with_context(short_name=False).create(activity_vals)

    ####################################################
    # Messaging methods
    ####################################################

    def _notify_change(self, message, subtype_xmlid='mail.mt_note'):
        for leave in self:
            leave.message_post(body=message, subtype_xmlid=subtype_xmlid)

            recipient = None
            if leave.user_id:
                recipient = leave.user_id.partner_id.id
            elif leave.employee_id:
                recipient = leave.employee_id.work_contact_id.id

            if recipient:
                self.env['mail.thread'].sudo().message_notify(
                    body=message,
                    partner_ids=[recipient],
                    subject=_('Your Time Off'),
                )

    def _track_subtype(self, init_values):
        if 'state' in init_values and self.state == 'validate':
            leave_notif_subtype = self.holiday_status_id.leave_notif_subtype_id
            return leave_notif_subtype or self.env.ref('hr_holidays.mt_leave')
        return super(HolidaysRequest, self)._track_subtype(init_values)

    def message_subscribe(self, partner_ids=None, subtype_ids=None):
        # due to record rule can not allow to add follower and mention on validated leave so subscribe through sudo
        if any(holiday.state in ['validate', 'validate1'] for holiday in self):
            self.check_access_rights('read')
            self.check_access_rule('read')
        #     return super(HolidaysRequest, self.sudo()).message_subscribe(partner_ids=partner_ids,
        #                                                                  subtype_ids=subtype_ids)
        # return super(HolidaysRequest, self).message_subscribe(partner_ids=partner_ids, subtype_ids=subtype_ids)

    @api.model
    def get_unusual_days(self, date_from, date_to=None):
        employee_id = self.env.context.get('employee_id', False)
        employee = self.env['hr.employee'].browse(employee_id) if employee_id else self.env.user.employee_id
        return employee.sudo(False)._get_unusual_days(date_from, date_to)

    def _to_utc(self, date, hour, resource):
        hour = float_to_time(float(hour))
        holiday_tz = timezone(resource.tz or self.env.user.tz or 'UTC')
        return holiday_tz.localize(datetime.combine(date, hour)).astimezone(UTC).replace(tzinfo=None)

    def _get_attendances_custom(self, request_date_from, request_date_to, day_period=None):
        self.ensure_one()
        domain = [
            ('calendar_id', '=', self.resource_calendar_id.id),
            ('display_type', '=', False),
            ('day_period', '!=', 'lunch'),
        ]
        if day_period:
            domain.append(('day_period', '=', day_period))
        attendances = self.env['resource.calendar.attendance'].read_group(domain,
                                                                          ['ids:array_agg(id)',
                                                                           'hour_from:min(hour_from)',
                                                                           'hour_to:max(hour_to)',
                                                                           'week_type', 'dayofweek', 'day_period'],
                                                                          ['week_type', 'dayofweek', 'day_period'],
                                                                          lazy=False)

        # Must be sorted by dayofweek ASC and day_period DESC
        attendances = sorted([DummyAttendance(group['hour_from'], group['hour_to'], group['dayofweek'],
                                              group['day_period'], group['week_type']) for group in attendances],
                             key=lambda att: (att.dayofweek, att.day_period != 'morning'))

        default_value = DummyAttendance(0, 0, 0, 'morning', False)

        if self.resource_calendar_id.two_weeks_calendar:
            # find week type of start_date
            start_week_type = self.env['resource.calendar.attendance'].get_week_type(request_date_from)
            attendance_actual_week = [att for att in attendances if
                                      att.week_type is False or int(att.week_type) == start_week_type]
            attendance_actual_next_week = [att for att in attendances if
                                           att.week_type is False or int(att.week_type) != start_week_type]
            # First, add days of actual week coming after date_from
            attendance_filtred = [att for att in attendance_actual_week if
                                  int(att.dayofweek) >= request_date_from.weekday()]
            # Second, add days of the other type of week
            attendance_filtred += list(attendance_actual_next_week)
            # Third, add days of actual week (to consider days that we have remove first because they coming before date_from)
            attendance_filtred += list(attendance_actual_week)
            end_week_type = self.env['resource.calendar.attendance'].get_week_type(request_date_to)
            attendance_actual_week = [att for att in attendances if
                                      att.week_type is False or int(att.week_type) == end_week_type]
            attendance_actual_next_week = [att for att in attendances if
                                           att.week_type is False or int(att.week_type) != end_week_type]
            attendance_filtred_reversed = list(
                reversed([att for att in attendance_actual_week if int(att.dayofweek) <= request_date_to.weekday()]))
            attendance_filtred_reversed += list(reversed(attendance_actual_next_week))
            attendance_filtred_reversed += list(reversed(attendance_actual_week))

            # find first attendance coming after first_day
            attendance_from = attendance_filtred[0]
            # find last attendance coming before last_day
            attendance_to = attendance_filtred_reversed[0]
        else:
            # find first attendance coming after first_day
            attendance_from = next((att for att in attendances if int(att.dayofweek) >= request_date_from.weekday()),
                                   attendances[0] if attendances else default_value)
            # find last attendance coming before last_day
            attendance_to = next(
                (att for att in reversed(attendances) if int(att.dayofweek) <= request_date_to.weekday()),
                attendances[-1] if attendances else default_value)

        return (attendance_from, attendance_to)

    ####################################################
    # Cron methods
    ####################################################

    @api.model
    def _cancel_invalid_leaves(self):
        inspected_date = fields.Date.today() + timedelta(days=31)
        start_datetime = datetime.combine(fields.Date.today(), datetime.min.time())
        end_datetime = datetime.combine(inspected_date, datetime.max.time())
        concerned_leaves = self.search([
            ('date_from', '>=', start_datetime),
            ('date_from', '<=', end_datetime),
            ('state', 'in', ['confirm', 'validate1', 'validate']),
        ], order='date_from desc')
        accrual_allocations = self.env['hr.leave.allocation'].search([
            ('employee_id', 'in', concerned_leaves.employee_id.ids),
            ('holiday_status_id', 'in', concerned_leaves.holiday_status_id.ids),
            ('allocation_type', '=', 'accrual'),
            ('date_from', '<=', end_datetime),
            '|',
            ('date_to', '>=', start_datetime),
            ('date_to', '=', False),
        ])
        # only take leaves linked to accruals
        concerned_leaves = concerned_leaves \
            .filtered(lambda leave: leave.holiday_status_id in accrual_allocations.holiday_status_id) \
            .sorted('date_from', reverse=True)
        reason = _("the accruated amount is insufficient for that duration.")
        for leave in concerned_leaves:
            to_recheck_leaves_per_leave_type = \
            concerned_leaves.employee_id._get_consumed_leaves(leave.holiday_status_id)[1]
            exceeding_duration = to_recheck_leaves_per_leave_type[leave.employee_id][leave.holiday_status_id][
                'exceeding_duration']
            if not exceeding_duration:
                continue
            leave._force_cancel(reason, 'mail.mt_note')

    @api.constrains('state', 'number_of_days', 'holiday_status_id')
    def _check_holidays(self):
        pass


class HolidaysAllocation(models.Model):
    """ Allocation Requests Access specifications: similar to leave requests """
    _inherit = "hr.leave.allocation"

    @api.depends_context('uid')
    def _compute_description(self):
        for allocation in self:
            if allocation.employee_company_id.id == self.env.ref('base.main_company').id:
                allocation.name = allocation.sudo().private_name
            else:
                super(HolidaysAllocation, self)._compute_description()


class ResourceCalendar(models.Model):
    _inherit = 'resource.calendar'

    def _get_resources_day_total(self, from_datetime, to_datetime, resources=None):
        """
        @return dict with hours of attendance in each day between `from_datetime` and `to_datetime`
        """
        self.ensure_one()
        if not resources:
            resources = self.env['resource.resource']
            resources_list = [resources]
        else:
            resources_list = list(resources) + [self.env['resource.resource']]
        # total hours per day:  retrieve attendances with one extra day margin,
        # in order to compute the total hours on the first and last days
        from_full = from_datetime
        to_full = to_datetime
        intervals = self._attendance_intervals_batch(from_full, to_full, resources=resources)
        saturdays_in_month = get_saturdays(from_full.month, from_full.year)
        result = defaultdict(lambda: defaultdict(float))
        for resource in resources_list:
            day_total = result[resource.id]
            for start, stop, meta in intervals[resource.id]:
                if start.day in saturdays_in_month:
                    if start.day == saturdays_in_month[1]:
                        continue
                    else:
                        day_total[start.date()] += 4
                        continue
                day_total[start.date()] += (stop - start).total_seconds() / 3600
        return result

    def _get_days_data(self, intervals, day_total):
        """
        helper function to compute duration of `intervals`
        expressed in days and hours.
        `day_total` is a dict {date: n_hours} with the number of hours for each day.
        """
        day_hours = defaultdict(float)
        for start, stop, meta in intervals:
            if start.day in get_saturdays(start.month, start.year):
                if start.day == get_saturdays(start.month, start.year)[1]:
                    continue
                else:
                    day_hours[start.date()] += 4
                    continue
            day_hours[start.date()] += (stop - start).total_seconds() / 3600

        # compute number of days as quarters
        for a in day_hours:
            if day_total[a]:
                float_utils.round(ROUNDING_FACTOR * day_hours[a] / self.hours_per_day) / ROUNDING_FACTOR

        days = sum(
            float_utils.round(ROUNDING_FACTOR * day_hours[day] / self.hours_per_day) / ROUNDING_FACTOR if day_total[
                day] else 0
            for day in day_hours
        )
        return {
            'days': days,
            'hours': sum(day_hours.values()),
        }


class HrLeaveAccrualLevel(models.Model):
    _inherit = 'hr.leave.accrual.level'

    cap_accrued_time = fields.Boolean("Cap accrued time", default=True)
    maximum_leave = fields.Float(
        'Limit to', digits=(16, 2), compute="_compute_maximum_leave", readonly=False, store=True,
        help="Choose a cap for this accrual.")

    @api.depends('cap_accrued_time')
    def _compute_maximum_leave(self):
        for level in self:
            level.maximum_leave = 100 if level.cap_accrued_time else 0


class AccrualPlan(models.Model):
    _inherit = "hr.leave.accrual.plan"

    added_value_type = fields.Selection([('days', 'Days'), ('hours', 'Hours')], compute='_compute_added_value_type', store=True)
    accrued_gain_time = fields.Selection([
        ("start", "At the start of the accrual period"),
        ("end", "At the end of the accrual period")],
        default="end", required=True)
    carryover_date = fields.Selection([
        ("year_start", "At the start of the year"),
        ("allocation", "At the allocation date"),
        ("other", "Other")],
        default="year_start", required=True, string="Carry-Over Time")
    is_based_on_worked_time = fields.Boolean("Based on worked time", compute="_compute_is_based_on_worked_time",
                                             store=True, readonly=False,
                                             help="If checked, the accrual period will be calculated according to the work days, not calendar days.")

    @api.depends("level_ids")
    def _compute_added_value_type(self):
        for plan in self:
            if plan.level_ids:
                plan.added_value_type = plan.level_ids[0].added_value_type

    @api.depends("accrued_gain_time")
    def _compute_is_based_on_worked_time(self):
        for plan in self:
            if plan.accrued_gain_time == "start":
                plan.is_based_on_worked_time = False



