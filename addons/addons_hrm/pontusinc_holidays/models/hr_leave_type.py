# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (c) 2005-2006 Axelor SARL. (http://www.axelor.com)
import logging
import pytz
from collections import defaultdict
from datetime import time, datetime
from odoo.tools import format_date
from odoo.tools.translate import _
from odoo.tools.float_utils import float_round
from odoo.osv import expression
from odoo import api, fields, models


class HrLeaveType(models.Model):
    _inherit = "hr.leave.type"

    ## add column PYC 29/2/2023
    max_allowed_negative = fields.Integer(string='Negative',
                                help="Determine the maximum number of days of deficit that this type of leave can reach. The minimum value must be 1",
                                default=False)
    allows_negative = fields.Boolean(string='Check Negative',
                                      help="If selected, the user's application may exceed the allocated number of days and the remaining days may be in deficit")
    time_application = fields.Selection(
        string="Time Application",
        selection=[
            ('in_month', 'In Month'),
            ('next_month', 'Next Month'),
        ], required=True, default='in_month'
    )
    responsible_ids = fields.Many2many(
        'res.users', 'hr_leave_type_res_users_rel', 'hr_leave_type_id', 'res_users_id',
        string='Notified Time Off Officer',
        domain=lambda self: [('groups_id', 'in', self.env.ref('hr_holidays.group_hr_holidays_user').id),
                             ('share', '=', False),
                             ('company_ids', 'in', self.env.company.id)],
        auto_join=True,
        help="Choose the Time Off Officers who will be notified to approve allocation or Time Off Request. If empty, nobody will be notified")
    closest_allocation_remaining = fields.Float(compute='_compute_leaves')
    is_draft = fields.Boolean(default=False,
                              string="Default status when requesting leave for this type of leave",
                              help="Choose default status when requesting leave for this type of leave")
    _sql_constraints = [(
        'check_negative',
        'CHECK(NOT allows_negative OR max_allowed_negative > 0)',
        'The negative amount must be greater than 0. If you want to set 0, disable the negative cap instead.'
    )]

    @api.model
    def get_days_all_request(self):
        return self.get_allocation_data_request()

    @api.model
    def _search_valid(self, operator, value):
        """ Returns leave_type ids for which a valid allocation exists
            or that don't need an allocation
            return [('id', domain_operator, [x['id'] for x in res])]
        """
        date_from = self._context.get('default_date_from') or fields.Date.today().strftime('%Y-1-1')
        date_to = self._context.get('default_date_to') or fields.Date.today().strftime('%Y-12-31')
        employee_id = self._context.get('default_employee_id',
                                        self._context.get('employee_id')) or self.env.user.employee_id.id

        if not isinstance(value, bool):
            raise ValueError('Invalid value: %s' % (value))
        if operator not in ['=', '!=']:
            raise ValueError('Invalid operator: %s' % (operator))
        # '!=' True or '=' False
        if (operator == '=') ^ value:
            new_operator = 'not in'
        # '=' True or '!=' False
        else:
            new_operator = 'in'

        leave_types = self.env['hr.leave.allocation'].search([
            ('employee_id', '=', employee_id),
            ('state', '=', 'validate'),
            ('date_from', '<=', date_to),
            '|',
            ('date_to', '>=', date_from),
            ('date_to', '=', False),
        ]).holiday_status_id

        return [('id', new_operator, leave_types.ids)]

    @api.depends('requires_allocation', 'max_leaves', 'virtual_remaining_leaves')
    def _compute_valid(self):
        date_from = self._context.get('default_date_from', fields.Datetime.today())
        date_to = self._context.get('default_date_to', fields.Datetime.today())
        employee_id = self._context.get('default_employee_id',
                                        self._context.get('employee_id', self.env.user.employee_id.id))
        for holiday_type in self:
            if holiday_type.requires_allocation == 'yes':
                allocations = self.env['hr.leave.allocation'].search([
                    ('holiday_status_id', '=', holiday_type.id),
                    ('allocation_type', '=', 'accrual'),
                    ('employee_id', '=', employee_id),
                    ('date_from', '<=', date_from),
                    '|',
                    ('date_to', '>=', date_to),
                    ('date_to', '=', False),
                ])
                allowed_excess = holiday_type.max_allowed_negative if holiday_type.allows_negative else 0
                allocations = allocations.filtered(lambda alloc:
                   alloc.allocation_type == 'accrual'
                   or (alloc.max_leaves > 0 and holiday_type.virtual_remaining_leaves > -allowed_excess))
                holiday_type.has_valid_allocation = bool(allocations)
            else:
                holiday_type.has_valid_allocation = True

    def _search_max_leaves(self, operator, value):
        value = float(value)
        employee = self.env['hr.employee']._get_contextual_employee()
        leaves = defaultdict(int)

        if employee:
            allocations = self.env['hr.leave.allocation'].search([
                ('employee_id', '=', employee.id),
                ('state', '=', 'validate')
            ])
            for allocation in allocations:
                leaves[allocation.holiday_status_id.id] += allocation.number_of_days
        valid_leave = []
        for leave in leaves:
            if operator == '>':
                if leaves[leave] > value:
                    valid_leave.append(leave)
            elif operator == '<':
                if leaves[leave] < value:
                    valid_leave.append(leave)
            elif operator == '=':
                if leaves[leave] == value:
                    valid_leave.append(leave)
            elif operator == '!=':
                if leaves[leave] != value:
                    valid_leave.append(leave)

        return [('id', 'in', valid_leave)]

    @api.depends_context('employee_id', 'default_employee_id')
    def _compute_leaves(self):
        employee = self.env['hr.employee']._get_contextual_employee()
        target_date = self._context['default_date_from'] if 'default_date_from' in self._context else None
        data_days = self.get_allocation_data(employee, target_date)[employee]
        for holiday_status in self:
            result = [item for item in data_days if item[0] == holiday_status.name]
            leave_type_tuple = result[0] if result else ('', {})
            holiday_status.max_leaves = leave_type_tuple[1].get('max_leaves', 0)
            holiday_status.leaves_taken = leave_type_tuple[1].get('leaves_taken', 0)
            holiday_status.virtual_remaining_leaves = leave_type_tuple[1].get('virtual_remaining_leaves', 0)
            holiday_status.closest_allocation_remaining = leave_type_tuple[1].get('closest_allocation_remaining', 0)

    def _compute_allocation_count(self):
        min_datetime = fields.Datetime.to_string(datetime.now().replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0))
        max_datetime = fields.Datetime.to_string(datetime.now().replace(month=12, day=31, hour=23, minute=59, second=59))
        domain = [
            ('holiday_status_id', 'in', self.ids),
            ('date_from', '>=', min_datetime),
            ('date_from', '<=', max_datetime),
            ('state', 'in', ('confirm', 'validate')),
        ]

        grouped_res = self.env['hr.leave.allocation']._read_group(
            domain,
            ['holiday_status_id'],
            ['holiday_status_id'],
        )
        grouped_dict = dict((data['holiday_status_id'][0], data['holiday_status_id_count']) for data in grouped_res)
        for allocation in self:
            allocation.allocation_count = grouped_dict.get(allocation.id, 0)

    def _compute_group_days_leave(self):
            min_datetime = fields.Datetime.to_string(datetime.now().replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0))
            max_datetime = fields.Datetime.to_string(datetime.now().replace(month=12, day=31, hour=23, minute=59, second=59))
            domain = [
                ('holiday_status_id', 'in', self.ids),
                ('date_from', '>=', min_datetime),
                ('date_from', '<=', max_datetime),
                ('state', 'in', ('validate', 'validate1', 'confirm')),
            ]
            grouped_res = self.env['hr.leave']._read_group(
                domain,
                ['holiday_status_id'],
                ['holiday_status_id'],
            )
            grouped_dict = dict((data['holiday_status_id'][0], data['holiday_status_id_count']) for data in grouped_res)
            for allocation in self:
                allocation.group_days_leave = grouped_dict.get(allocation.id, 0)

    def _compute_accrual_count(self):
        accrual_allocations = self.env['hr.leave.accrual.plan']._read_group([('time_off_type_id', 'in', self.ids)], ['time_off_type_id'], ['time_off_type_id'])
        mapped_data = dict((data['time_off_type_id'][0], data['time_off_type_id_count']) for data in accrual_allocations)
        for leave_type in self:
            leave_type.accrual_count = mapped_data.get(leave_type.id, 0)

    def requested_display_name(self):
        return self._context.get('holiday_status_name_get', True) and self._context.get('employee_id')

    @api.depends('requires_allocation', 'virtual_remaining_leaves', 'max_leaves', 'request_unit')
    @api.depends_context('holiday_status_name_get', 'employee_id', 'from_manager_leave_form')
    def _compute_display_name(self):
        if not self.requested_display_name():
            # leave counts is based on employee_id, would be inaccurate if not based on correct employee
            return super()._compute_display_name()
        for record in self:
            name = record.name
            if record.requires_allocation == "yes" and not self._context.get('from_manager_leave_form'):
                name = "{name} ({count})".format(
                    name=name,
                    count=_('%g remaining out of %g') % (
                        float_round(record.virtual_remaining_leaves, precision_digits=2) or 0.0,
                        float_round(record.max_leaves, precision_digits=2) or 0.0,
                    ) + (_(' hours') if record.request_unit == 'hour' else _(' days')),
                )
            record.display_name = name

    def action_see_days_allocated(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("hr_holidays.hr_leave_allocation_action_all")
        action['domain'] = [
            ('holiday_status_id', 'in', self.ids),
        ]
        action['context'] = {
            'default_holiday_type': 'department',
            'default_holiday_status_id': self.ids[0],
            'search_default_approved_state': 1,
            'search_default_year': 1,
        }
        return action

    def action_see_group_leaves(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("hr_holidays.hr_leave_action_action_approve_department")
        action['domain'] = [
            ('holiday_status_id', '=', self.ids[0]),
        ]
        action['context'] = {
            'default_holiday_status_id': self.ids[0],
        }
        return action

    @api.model
    def get_allocation_data_request(self, target_date=None):
        leave_types = self.search([
            '|',
            ('company_id', 'in', self.env.context.get('allowed_company_ids')),
            ('company_id', '=', False),
        ], order='id')
        employee = self.env['hr.employee']._get_contextual_employee()
        if employee:
            return leave_types.get_allocation_data(employee, target_date)[employee]
        return []

    def get_allocation_data(self, employees, target_date=None):
        allocation_data = defaultdict(list)
        if target_date and isinstance(target_date, str):
            target_date = datetime.fromisoformat(target_date).date()
        elif target_date and isinstance(target_date, datetime):
            target_date = target_date.date()
        elif not target_date:
            target_date = fields.Date.today()

        allocations_leaves_consumed, extra_data = employees.with_context(
            ignored_leave_ids=self.env.context.get('ignored_leave_ids')
        )._get_consumed_leaves(self, target_date)
        leave_type_requires_allocation = self.filtered(lambda lt: lt.requires_allocation == 'yes')

        for employee in employees:
            for leave_type in leave_type_requires_allocation:
                if len(allocations_leaves_consumed[employee][leave_type]) == 0:
                    continue
                lt_info = (
                    leave_type.name,
                    {
                        'remaining_leaves': 0,
                        'virtual_remaining_leaves': 0,
                        'max_leaves': 0,
                        'accrual_bonus': 0,
                        'leaves_taken': 0,
                        'virtual_leaves_taken': 0,
                        'leaves_requested': 0,
                        'leaves_approved': 0,
                        'closest_allocation_remaining': 0,
                        'closest_allocation_expire': False,
                        'holds_changes': False,
                        'total_virtual_excess': 0,
                        'virtual_excess_data': {},
                        'exceeding_duration': extra_data[employee][leave_type]['exceeding_duration'],
                        'request_unit': leave_type.request_unit,
                        'icon': leave_type.sudo().icon_id.url,
                        'has_accrual_allocation': False,
                        'allows_negative': leave_type.allows_negative,
                        'max_allowed_negative': leave_type.max_allowed_negative,
                    },
                    leave_type.requires_allocation,
                    leave_type.id)
                for excess_date, excess_days in extra_data[employee][leave_type]['excess_days'].items():
                    amount = excess_days['amount']
                    lt_info[1]['virtual_excess_data'].update({
                        excess_date.strftime('%Y-%m-%d'): excess_days
                    }),
                    if not leave_type.allows_negative:
                        continue
                    lt_info[1]['virtual_leaves_taken'] += amount
                    lt_info[1]['virtual_remaining_leaves'] -= amount
                    lt_info[1]['total_virtual_excess'] += amount
                    if excess_days['is_virtual']:
                        lt_info[1]['leaves_requested'] += amount
                    else:
                        lt_info[1]['leaves_approved'] += amount
                        lt_info[1]['leaves_taken'] += amount
                        lt_info[1]['remaining_leaves'] -= amount
                allocations_now = self.env['hr.leave.allocation']
                allocations_date = self.env['hr.leave.allocation']
                allocations_with_remaining_leaves = self.env['hr.leave.allocation']
                for allocation, data in allocations_leaves_consumed[employee][leave_type].items():
                    # We only need the allocation that are valid at the given date
                    if allocation:
                        if allocation.allocation_type == 'accrual':
                            lt_info[1]['has_accrual_allocation'] = True
                        today = fields.Date.today()
                        if allocation.date_from <= today and (not allocation.date_to or allocation.date_to >= today):
                            # we get each allocation available now to indicate visually if
                            # the future evaluation holds changes compared to now
                            allocations_now |= allocation
                        if allocation.date_from <= target_date and (
                                not allocation.date_to or allocation.date_to >= target_date):
                            # we get each allocation available now to indicate visually if
                            # the future evaluation holds changes compared to now
                            allocations_date |= allocation
                        if allocation.date_from > target_date:
                            continue
                        if allocation.date_to and allocation.date_to < target_date:
                            continue
                    lt_info[1]['remaining_leaves'] += data['remaining_leaves']
                    lt_info[1]['virtual_remaining_leaves'] += data['virtual_remaining_leaves']
                    lt_info[1]['max_leaves'] += data['max_leaves']
                    lt_info[1]['accrual_bonus'] += data['accrual_bonus']
                    lt_info[1]['leaves_taken'] += data['leaves_taken']
                    lt_info[1]['virtual_leaves_taken'] += data['virtual_leaves_taken']
                    lt_info[1]['leaves_requested'] += data['virtual_leaves_taken'] - data['leaves_taken']
                    lt_info[1]['leaves_approved'] += data['leaves_taken']
                    if data['virtual_remaining_leaves'] > 0:
                        allocations_with_remaining_leaves |= allocation
                closest_allocation = allocations_with_remaining_leaves[0] if allocations_with_remaining_leaves else \
                self.env['hr.leave.allocation']
                closest_allocations = allocations_with_remaining_leaves.filtered(
                    lambda a: a.date_to == closest_allocation.date_to)
                closest_allocation_remaining = 0
                for closest_allocation in closest_allocations:
                    closest_allocation_remaining += \
                    allocations_leaves_consumed[employee][leave_type][closest_allocation]['virtual_remaining_leaves']
                if closest_allocation.date_to:
                    closest_allocation_expire = format_date(self.env, closest_allocation.date_to)
                    calendar = employee.resource_calendar_id \
                               or employee.company_id.resource_calendar_id
                    # closest_allocation_duration corresponds to the time remaining before the allocation expires
                    closest_allocation_duration = \
                        calendar._attendance_intervals_batch(
                            datetime.combine(closest_allocation.date_to, time.min).replace(tzinfo=pytz.UTC),
                            datetime.combine(target_date, time.max).replace(tzinfo=pytz.UTC)) \
                            if leave_type.request_unit in ['hour'] \
                            else (closest_allocation.date_to - target_date).days + 1
                else:
                    closest_allocation_expire = False
                    closest_allocation_duration = False
                # the allocations are assumed to be different from today's allocations if there is any
                # accrual days granted or if there is any difference between allocations now and on the selected date
                holds_changes = (lt_info[1]['accrual_bonus'] > 0
                                 or bool(allocations_date - allocations_now)
                                 or bool(allocations_now - allocations_date)) \
                                and target_date != fields.Date.today()
                lt_info[1].update({
                    'closest_allocation_remaining': closest_allocation_remaining,
                    'closest_allocation_expire': closest_allocation_expire,
                    'closest_allocation_duration': closest_allocation_duration,
                    'holds_changes': holds_changes,
                })
                if not self.env.context.get('from_dashboard', False) or lt_info[1]['max_leaves']:
                    allocation_data[employee].append(lt_info)
        for employee in allocation_data:
            for leave_type_data in allocation_data[employee]:
                for key, value in leave_type_data[1].items():
                    if isinstance(value, float):
                        leave_type_data[1][key] = round(value, 2)
        return allocation_data

