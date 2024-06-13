# Part of Odoo. See LICENSE file for full copyright and licensing details.
import pytz
import math
import itertools
from datetime import datetime, date, time
from collections import defaultdict
from dateutil.relativedelta import relativedelta
from pytz import timezone, utc
from odoo.addons.hr_holidays.models.hr_leave import get_employee_from_context
from random import randint
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_round
from odoo.osv import expression
from dateutil.rrule import rrule, DAILY
from itertools import chain
from odoo.tools import posix_to_ldml, float_utils, format_date, format_duration, pycompat

HOURS_PER_DAY = 8
# This will generate 16th of days
ROUNDING_FACTOR = 16
MONTHS_TO_INTEGER = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6, "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}


def get_timedelta(qty, granularity):
    """
        Helper to get a `relativedelta` object for the given quantity and interval unit.
        :param qty: the number of unit to apply on the timedelta to return
        :param granularity: Type of period in string, can be year, quarter, month, week, day or hour.

    """
    switch = {
        'hour': relativedelta(hours=qty),
        'day': relativedelta(days=qty),
        'week': relativedelta(weeks=qty),
        'month': relativedelta(months=qty),
        'year': relativedelta(years=qty),
    }
    return switch[granularity]


def string_to_datetime(value):
    """ Convert the given string value to a datetime in UTC. """
    return utc.localize(fields.Datetime.from_string(value))


def datetime_to_string(dt):
    """ Convert the given datetime (converted in UTC) to a string value. """
    return fields.Datetime.to_string(dt.astimezone(utc))


def _boundaries(intervals, opening, closing):
    """ Iterate on the boundaries of intervals. """
    for start, stop, recs in intervals:
        if start < stop:
            yield (start, opening, recs)
            yield (stop, closing, recs)


class Intervals(object):
    """ Collection of ordered disjoint intervals with some associated records.
        Each interval is a triple ``(start, stop, records)``, where ``records``
        is a recordset.
    """
    def __init__(self, intervals=()):
        self._items = []
        if intervals:
            # normalize the representation of intervals
            append = self._items.append
            starts = []
            recses = []
            for value, flag, recs in sorted(_boundaries(intervals, 'start', 'stop')):
                if flag == 'start':
                    starts.append(value)
                    recses.append(recs)
                else:
                    start = starts.pop()
                    if not starts:
                        append((start, value, recses[0].union(*recses)))
                        recses.clear()

    def __bool__(self):
        return bool(self._items)

    def __len__(self):
        return len(self._items)

    def __iter__(self):
        return iter(self._items)

    def __reversed__(self):
        return reversed(self._items)

    def __or__(self, other):
        """ Return the union of two sets of intervals. """
        return Intervals(chain(self._items, other._items))

    def __and__(self, other):
        """ Return the intersection of two sets of intervals. """
        return self._merge(other, False)

    def __sub__(self, other):
        """ Return the difference of two sets of intervals. """
        return self._merge(other, True)

    def _merge(self, other, difference):
        """ Return the difference or intersection of two sets of intervals. """
        result = Intervals()
        append = result._items.append

        # using 'self' and 'other' below forces normalization
        bounds1 = _boundaries(self, 'start', 'stop')
        bounds2 = _boundaries(other, 'switch', 'switch')

        start = None                    # set by start/stop
        recs1 = None                    # set by start
        enabled = difference            # changed by switch
        for value, flag, recs in sorted(chain(bounds1, bounds2)):
            if flag == 'start':
                start = value
                recs1 = recs
            elif flag == 'stop':
                if enabled and start < value:
                    append((start, value, recs1))
                start = None
            else:
                if not enabled and start is not None:
                    start = value
                if enabled and start is not None and start < value:
                    append((start, value, recs1))
                enabled = not enabled

        return result


def make_aware(dt):
    """ Return ``dt`` with an explicit timezone, together with a function to
        convert a datetime to the same (naive or aware) timezone as ``dt``.
    """
    if dt.tzinfo:
        return dt, lambda val: val.astimezone(dt.tzinfo)
    return dt.replace(tzinfo=utc), lambda val: val.astimezone(utc).replace(tzinfo=None)


def float_to_time(hours):
    """ Convert a number of hours into a time object. """
    if hours == 24.0:
        return time.max
    fractional, integral = math.modf(hours)
    return time(int(integral), int(float_round(60 * fractional, precision_digits=0)), 0)


class Employee(models.AbstractModel):
    _inherit = 'hr.employee.base'

    def _compute_allocation_count(self):
        # Don't get allocations that are expired
        current_date = date.today()
        data = self.env['hr.leave.allocation']._read_group([
            ('employee_id', 'in', self.ids),
            ('holiday_status_id.active', '=', True),
            ('holiday_status_id.requires_allocation', '=', 'yes'),
            ('state', '=', 'validate'),
            ('date_from', '<=', current_date),
            '|',
            ('date_to', '=', False),
            ('date_to', '>=', current_date),
        ], ['employee_id'], ['__count', 'number_of_days:sum'])
        rg_results = {employee.id: (count, days) for employee, count, days in data}
        for employee in self:
            count, days = rg_results.get(employee.id, (0, 0))
            employee.allocation_count = float_round(days, precision_digits=2)
            employee.allocations_count = count

    def _compute_allocation_remaining_display(self):
        current_date = date.today()
        allocations = self.env['hr.leave.allocation'].search([('employee_id', 'in', self.ids)])
        leaves_taken = self._get_consumed_leaves(allocations.holiday_status_id)[0]
        for employee in self:
            employee_remaining_leaves = 0
            employee_max_leaves = 0
            for leave_type in leaves_taken[employee]:
                if leave_type.requires_allocation == 'no':
                    continue
                for allocation in leaves_taken[employee][leave_type]:
                    if allocation and allocation.date_from <= current_date\
                            and (not allocation.date_to or allocation.date_to >= current_date):
                        virtual_remaining_leaves = leaves_taken[employee][leave_type][allocation]['virtual_remaining_leaves']
                        employee_remaining_leaves += virtual_remaining_leaves\
                            if leave_type.request_unit in ['day', 'half_day']\
                            else virtual_remaining_leaves / (employee.resource_calendar_id.hours_per_day or HOURS_PER_DAY)
                        employee_max_leaves += allocation.number_of_days
            employee.allocation_remaining_display = "%g" % float_round(employee_remaining_leaves, precision_digits=2)
            employee.allocation_display = "%g" % float_round(employee_max_leaves, precision_digits=2)

    def _compute_leave_status(self):
        # Used SUPERUSER_ID to forcefully get status of other user's leave, to bypass record rule
        holidays = self.env['hr.leave'].sudo().search([
            ('employee_id', 'in', self.ids),
            ('date_from', '<=', fields.Datetime.now()),
            ('date_to', '>=', fields.Datetime.now()),
            ('state', '=', 'validate'),
        ])
        leave_data = {}
        for holiday in holidays:
            leave_data[holiday.employee_id.id] = {}
            leave_data[holiday.employee_id.id]['leave_date_from'] = holiday.date_from.date()
            leave_data[holiday.employee_id.id]['leave_date_to'] = holiday.date_to.date()
            leave_data[holiday.employee_id.id]['current_leave_state'] = holiday.state

        for employee in self:
            employee.leave_date_from = leave_data.get(employee.id, {}).get('leave_date_from')
            employee.leave_date_to = leave_data.get(employee.id, {}).get('leave_date_to')
            employee.current_leave_state = leave_data.get(employee.id, {}).get('current_leave_state')
            employee.is_absent = leave_data.get(employee.id) and leave_data.get(employee.id, {}).get('current_leave_state') in ['validate']

    def _search_absent_employee(self, operator, value):
        if operator not in ('=', '!=') or not isinstance(value, bool):
            raise UserError(_('Operation not supported'))
        # This search is only used for the 'Absent Today' filter however
        # this only returns employees that are absent right now.
        today_date = datetime.utcnow().date()
        today_start = fields.Datetime.to_string(today_date)
        today_end = fields.Datetime.to_string(today_date + relativedelta(hours=23, minutes=59, seconds=59))
        holidays = self.env['hr.leave'].sudo().search([
            ('employee_id', '!=', False),
            ('state', '=', 'validate'),
            ('date_from', '<=', today_end),
            ('date_to', '>=', today_start),
        ])
        operator = ['in', 'not in'][(operator == '=') != value]
        return [('id', operator, holidays.mapped('employee_id').ids)]

    def write(self, values):
        if 'parent_id' in values:
            manager = self.env['hr.employee'].browse(values['parent_id']).user_id
            if manager:
                to_change = self.filtered(lambda e: e.leave_manager_id == e.parent_id.user_id or not e.leave_manager_id)
                to_change.write({'leave_manager_id': values.get('leave_manager_id', manager.id)})

        old_managers = self.env['res.users']
        if 'leave_manager_id' in values:
            old_managers = self.mapped('leave_manager_id')
            if values['leave_manager_id']:
                leave_manager = self.env['res.users'].browse(values['leave_manager_id'])
                old_managers -= leave_manager
                approver_group = self.env.ref('hr_holidays.group_hr_holidays_responsible', raise_if_not_found=False)
                if approver_group and not leave_manager.has_group('hr_holidays.group_hr_holidays_responsible'):
                    leave_manager.sudo().write({'groups_id': [(4, approver_group.id)]})

        res = super(Employee, self.with_context(no_leave_resource_calendar_update=True)).write(values)
        # remove users from the Responsible group if they are no longer leave managers
        old_managers.sudo()._clean_leave_responsible_users()

        # Change the resource calendar of the employee's leaves in the future
        # Other modules can disable this behavior by setting the context key
        # 'no_leave_resource_calendar_update'
        if 'resource_calendar_id' in values and not self.env.context.get('no_leave_resource_calendar_update'):
            try:
                self.env['hr.leave'].search([
                    ('employee_id', 'in', self.ids),
                    ('resource_calendar_id', '!=', int(values['resource_calendar_id'])),
                    ('date_from', '>', fields.Datetime.now())]).write({'resource_calendar_id': values['resource_calendar_id']})
            except ValidationError:
                raise ValidationError(_("Changing this working schedule results in the affected employee(s) not having enough "
                                        "leaves allocated to accomodate for their leaves already taken in the future. Please "
                                        "review this employee's leaves and adjust their allocation accordingly."))

        if 'parent_id' in values or 'department_id' in values:
            today_date = fields.Datetime.now()
            hr_vals = {}
            if values.get('parent_id') is not None:
                hr_vals['manager_id'] = values['parent_id']
            if values.get('department_id') is not None:
                hr_vals['department_id'] = values['department_id']
            holidays = self.env['hr.leave'].sudo().search(['|', ('state', 'in', ['draft', 'confirm']), ('date_from', '>', today_date), ('employee_id', 'in', self.ids)])
            holidays.write(hr_vals)
            allocations = self.env['hr.leave.allocation'].sudo().search([('state', 'in', ['draft', 'confirm']), ('employee_id', 'in', self.ids)])
            allocations.write(hr_vals)
        return res


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    def _compute_current_leave(self):
        self.current_leave_id = False

        holidays = self.env['hr.leave'].sudo().search([
            ('employee_id', 'in', self.ids),
            ('date_from', '<=', fields.Datetime.now()),
            ('date_to', '>=', fields.Datetime.now()),
            ('state', 'not in', ('cancel', 'refuse'))
        ])
        for holiday in holidays:
            employee = self.filtered(lambda e: e.id == holiday.employee_id.id)
            employee.current_leave_id = holiday.holiday_status_id.id

    def _is_leave_user(self):
        return self == self.env.user.employee_id and self.user_has_groups('hr_holidays.group_hr_holidays_user')


    def _get_public_holidays(self, date_start, date_end):
        domain = [
            ('resource_id', '=', False),
            ('company_id', 'in', self.env.companies.ids),
            ('date_from', '<=', date_end),
            ('date_to', '>=', date_start),
        ]

        # a user with hr_holidays permissions will be able to see all public holidays from his calendar
        if not self._is_leave_user():
            domain += [
                '|',
                ('calendar_id', '=', False),
                ('calendar_id', '=', self.resource_calendar_id.id),
            ]

        return self.env['resource.calendar.leaves'].search(domain)


    @api.model
    def _get_contextual_employee(self):
        ctx = self.env.context
        return self.browse(ctx.get('employee_id') or ctx.get('default_employee_id')) or self.env.user.employee_id

    def _get_consumed_leaves(self, leave_types, target_date=False, ignore_future=False):
        employees = self or self._get_contextual_employee()
        leaves_domain = [
            ('holiday_status_id', 'in', leave_types.ids),
            ('employee_id', 'in', employees.ids),
            ('state', 'in', ['confirm', 'validate1', 'validate']),
        ]
        if self.env.context.get('ignored_leave_ids'):
            leaves_domain.append(('id', 'not in', self.env.context.get('ignored_leave_ids')))

        if not target_date:
            target_date = fields.Date.today()
        if ignore_future:
            leaves_domain.append(('date_from', '<=', target_date))
        leaves = self.env['hr.leave'].search(leaves_domain)
        leaves_per_employee_type = defaultdict(lambda: defaultdict(lambda: self.env['hr.leave']))
        for leave in leaves:
            leaves_per_employee_type[leave.employee_id][leave.holiday_status_id] |= leave

        allocations = self.env['hr.leave.allocation'].with_context(active_test=False).search([
            ('employee_id', 'in', employees.ids),
            ('holiday_status_id', 'in', leave_types.ids),
            ('state', '=', 'validate'),
        ]).filtered(lambda al: al.active or not al.employee_id.active)
        allocations_per_employee_type = defaultdict(lambda: defaultdict(lambda: self.env['hr.leave.allocation']))
        for allocation in allocations:
            allocations_per_employee_type[allocation.employee_id][allocation.holiday_status_id] |= allocation
        allocations_leaves_consumed = defaultdict(
            lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: 0))))

        to_recheck_leaves_per_leave_type = defaultdict(lambda:
                                                       defaultdict(lambda: {
                                                           'excess_days': defaultdict(lambda: {
                                                               'amount': 0,
                                                               'is_virtual': True,
                                                           }),
                                                           'total_virtual_excess': 0,
                                                           'exceeding_duration': 0,
                                                           'to_recheck_leaves': self.env['hr.leave']
                                                       })
                                                       )
        for allocation in allocations:
            allocation_data = allocations_leaves_consumed[allocation.employee_id][allocation.holiday_status_id][
                allocation]
            future_leaves = 0
            if allocation.allocation_type == 'accrual':
                future_leaves = allocation._get_future_leaves_on(target_date)
            max_leaves = allocation.number_of_hours_display \
                if allocation.type_request_unit in ['hour'] \
                else allocation.number_of_days_display
            max_leaves += future_leaves
            allocation_data.update({
                'allocation_type': allocation.allocation_type,
                'max_leaves': max_leaves,
                'accrual_bonus': future_leaves,
                'virtual_remaining_leaves': max_leaves,
                'remaining_leaves': max_leaves,
                'leaves_taken': 0,
                'virtual_leaves_taken': 0,
            })

        for employee in employees:
            for leave_type in leave_types:
                allocations_with_date_to = self.env['hr.leave.allocation']
                allocations_without_date_to = self.env['hr.leave.allocation']
                for leave_allocation in allocations_per_employee_type[employee][leave_type]:
                    if leave_allocation.date_to:
                        allocations_with_date_to |= leave_allocation
                    else:
                        allocations_without_date_to |= leave_allocation
                sorted_leave_allocations = allocations_with_date_to.sorted(key='date_to') + allocations_without_date_to

                if leave_type.request_unit in ['day', 'half_day']:
                    leave_duration_field = 'number_of_days'
                    leave_unit = 'days'
                else:
                    leave_duration_field = 'number_of_hours_display'
                    leave_unit = 'hours'

                leave_type_data = allocations_leaves_consumed[employee][leave_type]
                for leave in leaves_per_employee_type[employee][leave_type].sorted('date_from'):
                    leave_duration = leave[leave_duration_field]
                    skip_excess = False
                    if leave_type.requires_allocation == 'yes':
                        for allocation in sorted_leave_allocations:
                            # We don't want to include future leaves linked to accruals into the total count of available leaves.
                            # However, we'll need to check if those leaves take more than what will be accrued in total of those days
                            # to give a warning if the total exceeds what will be accrued.
                            if allocation.allocation_type == 'accrual' and leave.date_from.date() > target_date:
                                to_recheck_leaves_per_leave_type[employee][leave_type]['to_recheck_leaves'] |= leave
                                skip_excess = True
                                continue
                            if allocation.date_from > leave.date_to.date() or (
                                    allocation.date_to and allocation.date_to < leave.date_from.date()):
                                continue
                            interval_start = max(
                                leave.date_from,
                                datetime.combine(allocation.date_from, time.min)
                            )
                            interval_end = min(
                                leave.date_to,
                                datetime.combine(allocation.date_to, time.max)
                                if allocation.date_to else leave.date_to
                            )
                            duration = leave[leave_duration_field]
                            if leave.date_from != interval_start or leave.date_to != interval_end:
                                duration_info = employee._get_calendar_attendances(
                                    interval_start.replace(tzinfo=pytz.UTC), interval_end.replace(tzinfo=pytz.UTC))
                                duration = duration_info['hours' if leave_unit == 'hours' else 'days']
                            max_allowed_duration = min(
                                duration,
                                leave_type_data[allocation]['virtual_remaining_leaves']
                            )

                            if not max_allowed_duration:
                                continue

                            allocated_time = min(max_allowed_duration, leave_duration)
                            leave_type_data[allocation]['virtual_leaves_taken'] += allocated_time
                            leave_type_data[allocation]['virtual_remaining_leaves'] -= allocated_time
                            if leave.state == 'validate':
                                leave_type_data[allocation]['leaves_taken'] += allocated_time
                                leave_type_data[allocation]['remaining_leaves'] -= allocated_time

                            leave_duration -= allocated_time
                            if not leave_duration:
                                break
                        if round(leave_duration, 2) > 0 and not skip_excess:
                            to_recheck_leaves_per_leave_type[employee][leave_type]['excess_days'][
                                leave.date_to.date()] = {
                                'amount': leave_duration,
                                'is_virtual': leave.state != 'validate',
                                'leave_id': leave.id,
                            }
                    else:
                        if leave_unit == 'hour':
                            allocated_time = leave.number_of_hours_display
                        else:
                            allocated_time = leave.number_of_days_display
                        leave_type_data[False]['virtual_leaves_taken'] += allocated_time
                        leave_type_data[False]['virtual_remaining_leaves'] = 0
                        leave_type_data[False]['remaining_leaves'] = 0
                        if leave.state == 'validate':
                            leave_type_data[False]['leaves_taken'] += allocated_time

        for employee in to_recheck_leaves_per_leave_type:
            for leave_type in to_recheck_leaves_per_leave_type[employee]:
                content = to_recheck_leaves_per_leave_type[employee][leave_type]
                consumed_content = allocations_leaves_consumed[employee][leave_type]
                if content['to_recheck_leaves']:
                    date_to_simulate = max(content['to_recheck_leaves'].mapped('date_from')).date()
                    latest_accrual_bonus = 0
                    date_accrual_bonus = 0
                    virtual_remaining = 0
                    additional_leaves_duration = 0
                    for allocation in consumed_content:
                        latest_accrual_bonus += allocation._get_future_leaves_on(date_to_simulate)
                        date_accrual_bonus += consumed_content[allocation]['accrual_bonus']
                        virtual_remaining += consumed_content[allocation]['virtual_remaining_leaves']
                    for leave in content['to_recheck_leaves']:
                        additional_leaves_duration += leave.number_of_hours if leave_type.request_unit == 'hours' else leave.number_of_days
                    latest_remaining = virtual_remaining - date_accrual_bonus + latest_accrual_bonus
                    content['exceeding_duration'] = round(min(0, latest_remaining - additional_leaves_duration), 2)

        return (allocations_leaves_consumed, to_recheck_leaves_per_leave_type)


class ResourceCalendar(models.Model):
    _inherit = 'resource.calendar'

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        if not res.get('name') and res.get('company_id'):
            res['name'] = _('Working Hours of %s', self.env['res.company'].browse(res['company_id']).name)
        if 'attendance_ids' in fields and not res.get('attendance_ids'):
            company_id = res.get('company_id', self.env.company.id)
            company = self.env['res.company'].browse(company_id)
            company_attendance_ids = company.resource_calendar_id.attendance_ids
            if not company.resource_calendar_id.two_weeks_calendar and company_attendance_ids:
                res['attendance_ids'] = [
                    (0, 0, {
                        'name': attendance.name,
                        'dayofweek': attendance.dayofweek,
                        'hour_from': attendance.hour_from,
                        'hour_to': attendance.hour_to,
                        'day_period': attendance.day_period,
                    })
                    for attendance in company_attendance_ids
                ]
            else:
                res['attendance_ids'] = [
                    (0, 0, {'name': _('Monday Morning'), 'dayofweek': '0', 'hour_from': 8, 'hour_to': 12,
                            'day_period': 'morning'}),
                    (0, 0, {'name': _('Monday Lunch'), 'dayofweek': '0', 'hour_from': 12, 'hour_to': 13,
                            'day_period': 'lunch'}),
                    (0, 0, {'name': _('Monday Afternoon'), 'dayofweek': '0', 'hour_from': 13, 'hour_to': 17,
                            'day_period': 'afternoon'}),
                    (0, 0, {'name': _('Tuesday Morning'), 'dayofweek': '1', 'hour_from': 8, 'hour_to': 12,
                            'day_period': 'morning'}),
                    (0, 0, {'name': _('Tuesday Lunch'), 'dayofweek': '1', 'hour_from': 12, 'hour_to': 13,
                            'day_period': 'lunch'}),
                    (0, 0, {'name': _('Tuesday Afternoon'), 'dayofweek': '1', 'hour_from': 13, 'hour_to': 17,
                            'day_period': 'afternoon'}),
                    (0, 0, {'name': _('Wednesday Morning'), 'dayofweek': '2', 'hour_from': 8, 'hour_to': 12,
                            'day_period': 'morning'}),
                    (0, 0, {'name': _('Wednesday Lunch'), 'dayofweek': '2', 'hour_from': 12, 'hour_to': 13,
                            'day_period': 'lunch'}),
                    (0, 0, {'name': _('Wednesday Afternoon'), 'dayofweek': '2', 'hour_from': 13, 'hour_to': 17,
                            'day_period': 'afternoon'}),
                    (0, 0, {'name': _('Thursday Morning'), 'dayofweek': '3', 'hour_from': 8, 'hour_to': 12,
                            'day_period': 'morning'}),
                    (0, 0, {'name': _('Thursday Lunch'), 'dayofweek': '3', 'hour_from': 12, 'hour_to': 13,
                            'day_period': 'lunch'}),
                    (0, 0, {'name': _('Thursday Afternoon'), 'dayofweek': '3', 'hour_from': 13, 'hour_to': 17,
                            'day_period': 'afternoon'}),
                    (0, 0, {'name': _('Friday Morning'), 'dayofweek': '4', 'hour_from': 8, 'hour_to': 12,
                            'day_period': 'morning'}),
                    (0, 0, {'name': _('Friday Lunch'), 'dayofweek': '4', 'hour_from': 12, 'hour_to': 13,
                            'day_period': 'lunch'}),
                    (0, 0, {'name': _('Friday Afternoon'), 'dayofweek': '4', 'hour_from': 13, 'hour_to': 17,
                            'day_period': 'afternoon'})
                ]
        return res

    @api.depends('company_id')
    def _compute_attendance_ids(self):
        for calendar in self.filtered(lambda c: not c._origin or c._origin.company_id != c.company_id and c.company_id):
            company_calendar = calendar.company_id.resource_calendar_id
            calendar.update({
                'two_weeks_calendar': company_calendar.two_weeks_calendar,
                'tz': company_calendar.tz,
                'attendance_ids': [(5, 0, 0)] + [
                    (0, 0, attendance._copy_attendance_vals()) for attendance in company_calendar.attendance_ids if
                    not attendance.resource_id]
            })

    def switch_calendar_type(self):
        if not self.two_weeks_calendar:
            self.attendance_ids.unlink()
            self.attendance_ids = [
                (0, 0, {
                    'name': 'First week',
                    'dayofweek': '0',
                    'sequence': '0',
                    'hour_from': 0,
                    'day_period': 'morning',
                    'week_type': '0',
                    'hour_to': 0,
                    'display_type':
                    'line_section'}),
                (0, 0, {
                    'name': 'Second week',
                    'dayofweek': '0',
                    'sequence': '25',
                    'hour_from': 0,
                    'day_period': 'morning',
                    'week_type': '1',
                    'hour_to': 0,
                    'display_type': 'line_section'}),
            ]

            self.two_weeks_calendar = True
            default_attendance = self.default_get('attendance_ids')['attendance_ids']
            for idx, att in enumerate(default_attendance):
                att[2]["week_type"] = '0'
                att[2]["sequence"] = idx + 1
            self.attendance_ids = default_attendance
            for idx, att in enumerate(default_attendance):
                att[2]["week_type"] = '1'
                att[2]["sequence"] = idx + 26
            self.attendance_ids = default_attendance
        else:
            self.two_weeks_calendar = False
            self.attendance_ids.unlink()
            self.attendance_ids = self.default_get('attendance_ids')['attendance_ids']

    def _attendance_intervals_batch(self, start_dt, end_dt, resources=None, domain=None, tz=None, lunch=False):
        assert start_dt.tzinfo and end_dt.tzinfo
        self.ensure_one()
        if not resources:
            resources = self.env['resource.resource']
            resources_list = [resources]
        else:
            resources_list = list(resources) + [self.env['resource.resource']]
        resource_ids = [r.id for r in resources_list]
        domain = domain if domain is not None else []
        domain = expression.AND([domain, [
            ('calendar_id', '=', self.id),
            ('resource_id', 'in', resource_ids),
            ('display_type', '=', False),
            ('day_period', '!=' if not lunch else '=', 'lunch'),
        ]])

        attendances = self.env['resource.calendar.attendance'].search(domain)
        # Since we only have one calendar to take in account
        # Group resources per tz they will all have the same result
        resources_per_tz = defaultdict(list)
        for resource in resources_list:
            resources_per_tz[tz or timezone((resource or self).tz)].append(resource)
        # Resource specific attendances
        attendance_per_resource = defaultdict(lambda: self.env['resource.calendar.attendance'])
        # Calendar attendances per day of the week
        # * 7 days per week * 2 for two week calendars
        attendances_per_day = [self.env['resource.calendar.attendance']] * 7 * 2
        weekdays = set()
        for attendance in attendances:
            if attendance.resource_id:
                attendance_per_resource[attendance.resource_id] |= attendance
            weekday = int(attendance.dayofweek)
            weekdays.add(weekday)
            if self.two_weeks_calendar:
                weektype = int(attendance.week_type)
                attendances_per_day[weekday + 7 * weektype] |= attendance
            else:
                attendances_per_day[weekday] |= attendance
                attendances_per_day[weekday + 7] |= attendance

        start = start_dt.astimezone(utc)
        end = end_dt.astimezone(utc)
        bounds_per_tz = {
            tz: (start_dt.astimezone(tz), end_dt.astimezone(tz))
            for tz in resources_per_tz.keys()
        }
        # Use the outer bounds from the requested timezones
        for tz, bounds in bounds_per_tz.items():
            start = min(start, bounds[0].replace(tzinfo=utc))
            end = max(end, bounds[1].replace(tzinfo=utc))
        # Generate once with utc as timezone
        days = rrule(DAILY, start.date(), until=end.date(), byweekday=weekdays)
        ResourceCalendarAttendance = self.env['resource.calendar.attendance']
        base_result = []
        per_resource_result = defaultdict(list)
        for day in days:
            week_type = ResourceCalendarAttendance.get_week_type(day)
            attendances = attendances_per_day[day.weekday() + 7 * week_type]
            for attendance in attendances:
                if (attendance.date_from and day.date() < attendance.date_from) or\
                    (attendance.date_to and attendance.date_to < day.date()):
                    continue
                day_from = datetime.combine(day, float_to_time(attendance.hour_from))
                day_to = datetime.combine(day, float_to_time(attendance.hour_to))
                if attendance.resource_id:
                    per_resource_result[attendance.resource_id].append((day_from, day_to, attendance))
                else:
                    base_result.append((day_from, day_to, attendance))


        # Copy the result localized once per necessary timezone
        # Strictly speaking comparing start_dt < time or start_dt.astimezone(tz) < time
        # should always yield the same result. however while working with dates it is easier
        # if all dates have the same format
        result_per_tz = {
            tz: [(max(bounds_per_tz[tz][0], tz.localize(val[0])),
                min(bounds_per_tz[tz][1], tz.localize(val[1])),
                val[2])
                    for val in base_result]
            for tz in resources_per_tz.keys()
        }
        result_per_resource_id = dict()
        for tz, resources in resources_per_tz.items():
            res = result_per_tz[tz]
            res_intervals = Intervals(res)
            for resource in resources:
                if resource in per_resource_result:
                    resource_specific_result = [(max(bounds_per_tz[tz][0], tz.localize(val[0])), min(bounds_per_tz[tz][1], tz.localize(val[1])), val[2])
                        for val in per_resource_result[resource]]
                    result_per_resource_id[resource.id] = Intervals(itertools.chain(res, resource_specific_result))
                else:
                    result_per_resource_id[resource.id] = res_intervals
        return result_per_resource_id

    def _leave_intervals_batch(self, start_dt, end_dt, resources=None, domain=None, tz=None, any_calendar=False):
        """ Return the leave intervals in the given datetime range.
            The returned intervals are expressed in specified tz or in the calendar's timezone.
        """
        assert start_dt.tzinfo and end_dt.tzinfo
        self.ensure_one()

        if not resources:
            resources = self.env['resource.resource']
            resources_list = [resources]
        else:
            resources_list = list(resources) + [self.env['resource.resource']]
        if domain is None:
            domain = [('time_type', '=', 'leave')]
        if not any_calendar:
            domain = domain + [('calendar_id', 'in', [False, self.id])]
        # for the computation, express all datetimes in UTC
        # Public leave don't have a resource_id
        domain = domain + [
            ('resource_id', 'in', [False] + [r.id for r in resources_list]),
            ('date_from', '<=', datetime_to_string(end_dt)),
            ('date_to', '>=', datetime_to_string(start_dt)),
        ]

        # retrieve leave intervals in (start_dt, end_dt)
        result = defaultdict(lambda: [])
        tz_dates = {}
        all_leaves = self.env['resource.calendar.leaves'].search(domain)
        for leave in all_leaves:
            leave_resource = leave.resource_id
            leave_company = leave.company_id
            leave_date_from = leave.date_from
            leave_date_to = leave.date_to
            for resource in resources_list:
                if leave_resource.id not in [False, resource.id] or (not leave_resource and resource and resource.company_id != leave_company):
                    continue
                tz = tz if tz else timezone((resource or self).tz)
                if (tz, start_dt) in tz_dates:
                    start = tz_dates[(tz, start_dt)]
                else:
                    start = start_dt.astimezone(tz)
                    tz_dates[(tz, start_dt)] = start
                if (tz, end_dt) in tz_dates:
                    end = tz_dates[(tz, end_dt)]
                else:
                    end = end_dt.astimezone(tz)
                    tz_dates[(tz, end_dt)] = end
                dt0 = string_to_datetime(leave_date_from).astimezone(tz)
                dt1 = string_to_datetime(leave_date_to).astimezone(tz)
                result[resource.id].append((max(start, dt0), min(end, dt1), leave))

        return {r.id: Intervals(result[r.id]) for r in resources_list}

    def _get_attendance_intervals_days_data(self, attendance_intervals):
        """
        helper function to compute duration of `intervals` that have
        'resource.calendar.attendance' records as payload (3rd element in tuple).
        expressed in days and hours.

        resource.calendar.attendance records have durations associated
        with them so this method merely calculates the proportion that is
        covered by the intervals.
        """
        day_hours = defaultdict(float)
        day_days = defaultdict(float)
        for start, stop, meta in attendance_intervals:
            # If the interval covers only a part of the original attendance, we
            # take durations in days proportionally to what is left of the interval.
            interval_hours = (stop - start).total_seconds() / 3600
            day_hours[start.date()] += interval_hours
            day_days[start.date()] += sum(meta.mapped('duration_days')) * interval_hours / sum(meta.mapped('duration_hours'))

        return {
            # Round the number of days to the closest 16th of a day.
            'days': sum(float_utils.round(ROUNDING_FACTOR * day_days[day]) / ROUNDING_FACTOR for day in day_days),
            'hours': sum(day_hours.values()),
        }

    def get_work_duration_data(self, from_datetime, to_datetime, compute_leaves=True, domain=None):
        """
            Get the working duration (in days and hours) for a given period, only
            based on the current calendar. This method does not use resource to
            compute it.

            `domain` is used in order to recognise the leaves to take,
            None means default value ('time_type', '=', 'leave')

            Returns a dict {'days': n, 'hours': h} containing the
            quantity of working time expressed as days and as hours.
        """
        # naive datetimes are made explicit in UTC
        from_datetime, dummy = make_aware(from_datetime)
        to_datetime, dummy = make_aware(to_datetime)

        # actual hours per day
        if compute_leaves:
            intervals = self._work_intervals_batch(from_datetime, to_datetime, domain=domain)[False]
        else:
            intervals = self._attendance_intervals_batch(from_datetime, to_datetime, domain=domain)[False]

        return self._get_attendance_intervals_days_data(intervals)

    def _get_max_number_of_hours(self, start, end):
        self.ensure_one()
        if not self.attendance_ids:
            return 0
        mapped_data = defaultdict(lambda: 0)
        for attendance in self.attendance_ids.filtered(lambda a: a.day_period != 'lunch' and ((not a.date_from or not a.date_to) or (a.date_from <= end.date() and a.date_to >= start.date()))):
            mapped_data[(attendance.week_type, attendance.dayofweek)] += attendance.hour_to - attendance.hour_from
        return max(mapped_data.values())


class ResourceCalendarAttendance(models.Model):
    _inherit = "resource.calendar.attendance"

    duration_hours = fields.Float(compute='_compute_duration_hours', string='Duration (hours)')
    duration_days = fields.Float(compute='_compute_duration_days', string='Duration (days)', store=True, readonly=False)
    day_period = fields.Selection([
        ('morning', 'Morning'),
        ('lunch', 'Break'),
        ('afternoon', 'Afternoon')], required=True, default='morning')

    @api.depends('hour_from', 'hour_to')
    def _compute_duration_hours(self):
        for attendance in self:
            attendance.duration_hours = (
                        attendance.hour_to - attendance.hour_from) if attendance.day_period != 'lunch' else 0

    @api.depends('day_period', 'hour_from', 'hour_to')
    def _compute_duration_days(self):
        for attendance in self:
            if attendance.day_period == 'lunch':
                attendance.duration_days = 0
            else:
                attendance.duration_days = 0.5 if attendance.duration_hours <= attendance.calendar_id.hours_per_day * 3 / 4 else 1


class ResourceCalendarLeaves(models.Model):
    _inherit = "resource.calendar.leaves"

    date_to = fields.Datetime('End Date', compute="_compute_date_to", readonly=False, required=True, store=True)

    @api.depends('date_from')
    def _compute_date_to(self):
            user_tz = timezone(self.env.user.tz or self._context.get('tz') or self.company_id.resource_calendar_id.tz or 'UTC')
            for leave in self:
                date_to_tz = user_tz.localize(leave.date_from) + relativedelta(hour=23, minute=59, second=59)
                leave.date_to = date_to_tz.astimezone(utc).replace(tzinfo=None)


class HolidaysAllocation(models.Model):
    """ Allocation Requests Access specifications: similar to leave requests """
    _inherit = "hr.leave.allocation"

    type_request_unit = fields.Selection([
        ('hour', 'Hours'),
        ('half_day', 'Half Day'),
        ('day', 'Day'),
    ], compute="_compute_type_request_unit")
    already_accrued = fields.Boolean()
    has_accrual_plan = fields.Boolean(compute='_compute_has_accrual_plan', string='Accrual Plan Available')
    # number_days_accrual_by_update_accrual = fields.Float(store=True)

    @api.depends_context('uid')
    @api.depends('holiday_status_id')
    def _compute_description(self):
        self.check_access_rights('read')
        self.check_access_rule('read')

        is_officer = self.env.user.has_group('hr_holidays.group_hr_holidays_user')

        for allocation in self:
            if is_officer or allocation.employee_id.user_id == self.env.user or allocation.employee_id.leave_manager_id == self.env.user:
                title = allocation.sudo().private_name
                if allocation.env.context.get('is_employee_allocation'):
                    if allocation.holiday_status_id:
                        allocation_duration = allocation.number_of_days_display if allocation.type_request_unit != 'hour' else allocation.number_of_hours_display
                        title = _("%s allocation request (%s %s)",
                                  allocation.holiday_status_id.name,
                                  allocation_duration,
                                  allocation.type_request_unit)
                    else:
                        title = _("Allocation Request")
                allocation.name = title
            else:
                allocation.name = '*****'

    @api.constrains('date_from', 'date_to')
    def _check_date_from_date_to(self):
        if any(allocation.date_to and allocation.date_from > allocation.date_to for allocation in self):
            raise UserError(_("The Start Date of the Validity Period must be anterior to the End Date."))

    @api.depends('accrual_plan_id')
    def _compute_has_accrual_plan(self):
        self.has_accrual_plan = bool(self.env['hr.leave.accrual.plan'].sudo().search_count([('active', '=', True)]))

    @api.depends('employee_id', 'holiday_status_id')
    def _compute_leaves(self):
        date_from = fields.Date.from_string(
            self._context['default_date_from']) if 'default_date_from' in self._context else fields.Date.today()
        employee_days_per_allocation = \
        self.employee_id._get_consumed_leaves(self.holiday_status_id, date_from, ignore_future=True)[0]
        for allocation in self:
            allocation.max_leaves = allocation.number_of_hours_display if allocation.type_request_unit == 'hour' else allocation.number_of_days
            allocation.leaves_taken = \
            employee_days_per_allocation[allocation.employee_id][allocation.holiday_status_id][allocation][
                'leaves_taken']

    @api.depends("allocation_type", "holiday_status_id", "accrual_plan_id")
    def _compute_type_request_unit(self):
        for allocation in self:
            allocation.type_request_unit = allocation._get_request_unit()

    def _get_request_unit(self):
        self.ensure_one()
        if self.allocation_type == "accrual" and self.accrual_plan_id:
            return self.accrual_plan_id.sudo().added_value_type
        elif self.allocation_type == "regular":
            return self.holiday_status_id.request_unit
        else:
            return "day"

    @api.depends('holiday_status_id', 'allocation_type', 'number_of_hours_display', 'number_of_days_display', 'date_to')
    def _compute_from_holiday_status_id(self):
        accrual_allocations = self.filtered(
            lambda alloc: alloc.allocation_type == 'accrual' and not alloc.accrual_plan_id and alloc.holiday_status_id)
        accruals_read_group = self.env['hr.leave.accrual.plan'].read_group(
            [('time_off_type_id', 'in', accrual_allocations.holiday_status_id.ids)],
            ['time_off_type_id', 'ids:array_agg(id)'],
            ['time_off_type_id'],
        )
        accruals_dict = {res['time_off_type_id'][0]: res['ids'] for res in accruals_read_group}
        for allocation in self:
            allocation_unit = allocation._get_request_unit()
            if allocation_unit != 'hour':
                allocation.number_of_days = allocation.number_of_days_display
            else:
                hours_per_day = allocation.employee_id.sudo().resource_calendar_id.hours_per_day \
                                or allocation.holiday_status_id.company_id.resource_calendar_id.hours_per_day \
                                or HOURS_PER_DAY
                allocation.number_of_days = allocation.number_of_hours_display / hours_per_day
            if allocation.accrual_plan_id.time_off_type_id.id not in (False, allocation.holiday_status_id.id):
                allocation.accrual_plan_id = False
            if allocation.allocation_type == 'accrual' and not allocation.accrual_plan_id:
                if allocation.holiday_status_id:
                    allocation.accrual_plan_id = accruals_dict.get(allocation.holiday_status_id.id, [False])[0]

    def _get_carryover_date(self, date_from):
        self.ensure_one()
        carryover_time = self.accrual_plan_id.carryover_date
        accrual_plan = self.accrual_plan_id
        carryover_date = False
        if carryover_time == 'year_start':
            carryover_date = date(date_from.year, 1, 1)
        elif carryover_time == 'allocation':
            carryover_date = date(date_from.year, self.date_from.month, self.date_from.day)
        else:
            carryover_date = date(date_from.year, MONTHS_TO_INTEGER[accrual_plan.carryover_month], accrual_plan.carryover_day)
        if date_from > carryover_date:
            carryover_date += relativedelta(years=1)
        return carryover_date

    def _add_days_to_allocation(self, current_level, current_level_maximum_leave, leaves_taken, period_start, period_end):
        days_to_add = self._process_accrual_plan_level(
            current_level, period_start, self.lastcall, period_end, self.nextcall)
        # self.number_days_accrual_by_update_accrual = days_to_add
        self.number_of_days += days_to_add
        if current_level.cap_accrued_time:
            self.number_of_days = min(self.number_of_days, current_level_maximum_leave + leaves_taken)

    def _get_accrual_plan_level_work_entry_prorata(self, level, start_period, start_date, end_period, end_date):
        self.ensure_one()
        datetime_min_time = datetime.min.time()
        start_dt = datetime.combine(start_date, datetime_min_time)
        end_dt = datetime.combine(end_date, datetime_min_time)
        worked = self.employee_id._get_work_days_data_batch(start_dt, end_dt, calendar=self.employee_id.resource_calendar_id)\
            [self.employee_id.id]['hours']
        if start_period != start_date or end_period != end_date:
            start_dt = datetime.combine(start_period, datetime_min_time)
            end_dt = datetime.combine(end_period, datetime_min_time)
            planned_worked = self.employee_id._get_work_days_data_batch(start_dt, end_dt, calendar=self.employee_id.resource_calendar_id)\
                [self.employee_id.id]['hours']
        else:
            planned_worked = worked
        left = self.employee_id.sudo()._get_leave_days_data_batch(start_dt, end_dt,
            domain=[('time_type', '=', 'leave')])[self.employee_id.id]['hours']
        if level.frequency == 'hourly':
            if level.accrual_plan_id.is_based_on_worked_time:
                work_entry_prorata = planned_worked
            else:
                work_entry_prorata = planned_worked + left
        else:
            work_entry_prorata = worked / (left + planned_worked) if (left + planned_worked) else 0
        return work_entry_prorata

    def _process_accrual_plan_level(self, level, start_period, start_date, end_period, end_date):
        """
        Returns the added days for that level
        """
        self.ensure_one()
        if level.frequency == 'hourly' or level.accrual_plan_id.is_based_on_worked_time:
            work_entry_prorata = self._get_accrual_plan_level_work_entry_prorata(level, start_period, start_date, end_period, end_date)
            added_value = work_entry_prorata * level.added_value
        else:
            added_value = level.added_value
        # Convert time in hours to time in days in case the level is encoded in hours
        if level.added_value_type == 'hour':
            added_value = added_value / (self.employee_id.sudo().resource_id.calendar_id.hours_per_day or HOURS_PER_DAY)
        period_prorata = 1
        if (start_period != start_date or end_period != end_date) and not level.accrual_plan_id.is_based_on_worked_time:
            period_days = (end_period - start_period)
            call_days = (end_date - start_date)
            period_prorata = min(1, call_days / period_days) if period_days else 1
        return added_value * period_prorata

    @api.depends(
        'holiday_type', 'mode_company_id', 'department_id',
        'category_id', 'employee_id', 'holiday_status_id',
        'type_request_unit', 'number_of_days',
    )
    def _compute_display_name(self):
        for allocation in self:
            if allocation.holiday_type == 'company':
                target = allocation.mode_company_id.name
            elif allocation.holiday_type == 'department':
                target = allocation.department_id.name
            elif allocation.holiday_type == 'category':
                target = allocation.category_id.name
            elif allocation.employee_id:
                target = allocation.employee_id.name
            elif len(allocation.employee_ids) <= 3:
                target = ', '.join(allocation.employee_ids.sudo().mapped('name'))
            else:
                target = _('%(first)s, %(second)s and %(amount)s others',
                           first=allocation.employee_ids[0].sudo().name,
                           second=allocation.employee_ids[1].sudo().name,
                           amount=len(allocation.employee_ids) - 2)

            allocation.display_name = _("Allocation of %s: %.2f %s to %s",
                                        allocation.holiday_status_id.sudo().name,
                                        allocation.number_of_hours_display if allocation.type_request_unit == 'hour' else allocation.number_of_days,
                                        _('hours') if allocation.type_request_unit == 'hour' else _('days'),
                                        target,
                                        )

    def _add_lastcalls(self):
        for allocation in self:
            if allocation.allocation_type != 'accrual':
                continue
            today = fields.Date.today()
            (current_level, current_level_idx) = allocation._get_current_accrual_plan_level_id(today)
            if not allocation.lastcall:
                if not current_level:
                    allocation.lastcall = today
                    continue
                allocation.lastcall = max(
                    current_level._get_previous_date(today),
                    allocation.date_from + get_timedelta(current_level.start_count, current_level.start_type)
                )
            if current_level and not allocation.nextcall:
                accrual_plan = allocation.accrual_plan_id
                allocation.nextcall = current_level._get_next_date(allocation.lastcall)
                if current_level_idx < (len(accrual_plan.level_ids) - 1) and accrual_plan.transition_mode == 'immediately':
                    next_level = accrual_plan.level_ids[current_level_idx + 1]
                    next_level_start = allocation.date_from + get_timedelta(next_level.start_count, next_level.start_type)
                    allocation.nextcall = min(allocation.nextcall, next_level_start)

    @api.model_create_multi
    def create(self, vals_list):
        """ Override to avoid automatic logging of creation """
        for values in vals_list:
            if 'state' in values and values['state'] not in ('draft', 'confirm'):
                raise UserError(_('Incorrect state for new allocation'))
            employee_id = values.get('employee_id', False)
            if not values.get('department_id'):
                values.update({'department_id': self.env['hr.employee'].browse(employee_id).department_id.id})
        allocations = super(HolidaysAllocation, self.with_context(mail_create_nosubscribe=True)).create(vals_list)
        allocations._add_lastcalls()
        for allocation in allocations:
            partners_to_subscribe = set()
            if allocation.employee_id.user_id:
                partners_to_subscribe.add(allocation.employee_id.user_id.partner_id.id)
            if allocation.validation_type == 'officer':
                partners_to_subscribe.add(allocation.employee_id.parent_id.user_id.partner_id.id)
                partners_to_subscribe.add(allocation.employee_id.leave_manager_id.partner_id.id)
            allocation.message_subscribe(partner_ids=tuple(partners_to_subscribe))
            if not self._context.get('import_file'):
                allocation.activity_update()
            if allocation.validation_type == 'no' and allocation.state == 'confirm':
                allocation.action_validate()
        return allocations

    def write(self, values):
        if not self.env.context.get('toggle_active') and not bool(values.get('active', True)):
            if any(allocation.state not in ['refuse'] for allocation in self):
                raise UserError(_('You cannot archive an allocation which is in confirm or validate state.'))
        employee_id = values.get('employee_id', False)
        if values.get('state'):
            self._check_approval_update(values['state'])

        self.add_follower(employee_id)

        if 'number_of_days_display' not in values and 'number_of_hours_display' not in values:
            return super().write(values)

        previous_consumed_leaves = self.employee_id._get_consumed_leaves(leave_types=self.holiday_status_id)
        result = super().write(values)
        consumed_leaves = self.employee_id._get_consumed_leaves(leave_types=self.holiday_status_id)
        for allocation in self:
            current_excess = dict(consumed_leaves[1]).get(allocation.employee_id, {}) \
                .get(allocation.holiday_status_id, {}).get('excess_days', {})
            previous_excess = dict(previous_consumed_leaves[1]).get(allocation.employee_id, {}) \
                .get(allocation.holiday_status_id, {}).get('excess_days', {})
            total_current_excess = sum(map(lambda leave_date: leave_date['amount'], current_excess.values()))
            total_previous_excess = sum(map(lambda leave_date: leave_date['amount'], previous_excess.values()))

            if total_current_excess <= total_previous_excess:
                continue
            lt = allocation.holiday_status_id
            if lt.allows_negative and total_current_excess <= lt.max_allowed_negative:
                continue
            raise ValidationError(
                _('You cannot reduce the duration below the duration of leaves already taken by the employee.'))

        return result

    def action_validate(self):
        to_validate = self.filtered(lambda alloc: alloc.state != 'validate')
        if to_validate:
            to_validate.write({
                'state': 'validate',
                'approver_id': self.env.user.employee_id.id
            })
            to_validate._action_validate_create_childs()
            to_validate.activity_update()
        return True

    def _action_validate_create_childs(self):
        allocation_vals = []
        for allocation in self:
            # In the case we are in holiday_type `employee` and there is only one employee we can keep the same allocation
            # Otherwise we do need to create an allocation for all employees to have a behaviour that is in line
            # with the other holiday_type
            if allocation.state == 'validate' and (allocation.holiday_type in ['category', 'department', 'company'] or
                (allocation.holiday_type == 'employee' and len(allocation.employee_ids) > 1)):
                if allocation.holiday_type == 'employee':
                    employees = allocation.employee_ids
                elif allocation.holiday_type == 'category':
                    employees = allocation.category_id.employee_ids
                elif allocation.holiday_type == 'department':
                    employees = allocation.department_id.member_ids
                else:
                    employees = self.env['hr.employee'].search([('company_id', '=', allocation.mode_company_id.id)])

                allocation_vals += allocation._prepare_holiday_values(employees)
        if allocation_vals:
            children = self.env['hr.leave.allocation'].with_context(
                mail_notify_force_send=False,
                mail_activity_automation_skip=True
            ).create(allocation_vals)
            children.filtered(lambda c: c.validation_type != 'no').action_validate()

    def action_refuse(self):
        current_employee = self.env.user.employee_id
        if any(allocation.state not in ['confirm', 'validate'] for allocation in self):
            raise UserError(_('Allocation request must be confirmed or validated in order to refuse it.'))

        days_per_allocation = self.employee_id._get_consumed_leaves(self.holiday_status_id)[0]

        for allocation in self:
            days_taken = days_per_allocation[allocation.employee_id][allocation.holiday_status_id][allocation]['virtual_leaves_taken']
            if days_taken > 0:
                raise UserError(_('You cannot refuse this allocation request since the employee has already taken leaves for it. Please refuse or delete those leaves first.'))

        self.write({'state': 'refuse', 'approver_id': current_employee.id})
        # If a category that created several holidays, cancel all related
        linked_requests = self.mapped('linked_request_ids')
        if linked_requests:
            linked_requests.action_refuse()
        self.activity_update()
        return True

    @api.onchange('date_from', 'accrual_plan_id', 'date_to')
    def _onchange_date_from(self):
        if self.allocation_type != 'accrual' or self.state == 'validate' or not self.accrual_plan_id \
                or not self.employee_id:
            return
        self.lastcall = self.date_from
        self.nextcall = False
        self.number_of_days_display = 0.0
        date_to = min(self.date_to, date.today()) if self.date_to else False
        self._process_accrual_plans(date_to)

    def activity_update(self):
        to_clean, to_do = self.env['hr.leave.allocation'], self.env['hr.leave.allocation']
        activity_vals = []
        for allocation in self:
            if allocation.validation_type != 'no':
                note = _(
                    'New Allocation Request created by %(user)s: %(count)s Days of %(allocation_type)s',
                    user=allocation.create_uid.name,
                    count=allocation.number_of_days,
                    allocation_type=allocation.holiday_status_id.name
                )
                if allocation.state == 'confirm':
                    if allocation.holiday_status_id.responsible_ids:
                        user_ids = allocation.sudo()._get_responsible_for_approval().ids
                        for user_id in user_ids:
                            activity_vals.append({
                                'activity_type_id': self.env.ref('hr_holidays.mail_act_leave_allocation_approval').id,
                                'automated': True,
                                'note': note,
                                'user_id': user_id,
                                'res_id': allocation.id,
                                'res_model_id': self.env.ref('hr_holidays.model_hr_leave_allocation').id,
                            })
                elif allocation.state == 'validate':
                    to_do |= allocation
                elif allocation.state == 'refuse':
                    to_clean |= allocation
        if activity_vals:
            self.env['mail.activity'].create(activity_vals)
        if to_clean:
            to_clean.activity_unlink(['hr_holidays.mail_act_leave_allocation_approval'])
        if to_do:
            to_do.activity_feedback(['hr_holidays.mail_act_leave_allocation_approval'])


    def _get_future_leaves_on(self, accrual_date):
        # As computing future accrual allocation days automatically updates the allocation,
        # We need to create a temporary copy of that allocation to return the difference in number of days
        # to see how much more days will be allocated from now until that date.
        self.ensure_one()
        if not accrual_date or accrual_date <= date.today():
            return 0

        if not (self.accrual_plan_id
                and self.state == 'validate'
                and self.allocation_type == 'accrual'
                and (not self.date_to or self.date_to > accrual_date)
                and (not self.nextcall or self.nextcall <= accrual_date)):
            return 0

        fake_allocation = self.env['hr.leave.allocation'].new(origin=self)
        fake_allocation.sudo()._process_accrual_plans(accrual_date, log=False)
        if self.type_request_unit in ['hour']:
            return float_round(fake_allocation.number_of_hours_display - self.number_of_hours_display, precision_digits=2)
        return round((fake_allocation.number_of_days - self.number_of_days), 2)




