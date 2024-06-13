import calendar
from collections import defaultdict
from datetime import timedelta, date, datetime

from dateutil.relativedelta import relativedelta
from odoo.tools import float_utils
from pytz import utc

from odoo import fields, models, api

ROUNDING_FACTOR = 16


def find_sundays(year, month):
    sundays = []
    saturday = []
    cal = calendar.monthcalendar(year, month)
    for week in cal:
        if week[calendar.SUNDAY] != 0:
            sundays.append(week[calendar.SUNDAY])
        if week[calendar.SATURDAY] != 0:
            saturday.append(week[calendar.SATURDAY])
    return {
        'sundays': sundays,
        'saturday': saturday
    }


class ResourceMixin(models.AbstractModel):
    _inherit = "resource.mixin"

    def _get_work_days_data(self, from_datetime, to_datetime, compute_leaves=True, calendar=None, domain=None):
        """
            By default the resource calendar is used, but it can be
            changed using the `calendar` argument.

            `domain` is used in order to recognise the leaves to take,
            None means default value ('time_type', '=', 'leave')

            Returns a dict {'days': n, 'hours': h} containing the
            quantity of working time expressed as days and as hours.
        """
        resource = self.resource_id
        calendar = calendar or self.resource_calendar_id

        # naive datetimes are made explicit in UTC
        if not from_datetime.tzinfo:
            from_datetime = from_datetime.replace(tzinfo=utc)
        if not to_datetime.tzinfo:
            to_datetime = to_datetime.replace(tzinfo=utc)

        # total hours per day: retrieve attendances with one extra day margin,
        # in order to compute the total hours on the first and last days
        from_full = from_datetime - timedelta(days=1)
        to_full = to_datetime + timedelta(days=1)
        intervals = calendar._attendance_intervals_batch(from_full, to_full, resource)
        day_total = defaultdict(float)
        for start, stop, meta in intervals[resource.id]:
            day_total[start.date()] += (stop - start).total_seconds() / 3600

        # actual hours per day
        if compute_leaves:
            intervals = calendar._work_intervals_batch(from_datetime, to_datetime, resource, domain)
        else:
            intervals = calendar._attendance_intervals_batch(from_datetime, to_datetime, resource)
        day_hours = defaultdict(float)
        for start, stop, meta in intervals[resource.id]:
            day_hours[start.date()] += (stop - start).total_seconds() / 3600

        # compute number of days as quarters
        days = sum(
            float_utils.round(ROUNDING_FACTOR * day_hours[day] / day_total[day]) / ROUNDING_FACTOR
            for day in day_hours
        )
        return {
            'days': days,
            'hours': sum(day_hours.values()),
        }


class TimesheetPenaltyCalculation(models.Model):
    _name = 'timesheet.penalty.calculation'

    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    employee_id = fields.Many2one('hr.employee', string='Employee')
    employee_code = fields.Char('Employee code')
    start_date = fields.Date('Start date')
    end_date = fields.Date('End date')
    standard_working_day = fields.Float('Standard working day')
    total_working_day = fields.Float('Total working day')
    total_holiday = fields.Float('Total holiday')
    total_leave = fields.Float('Total leave')
    total_not_leave = fields.Float('Total not leave')
    sum_arrive_late = fields.Float('Sum arrive late')
    total_arrive_late = fields.Float('Total arrive late')
    monthly_report_late = fields.Float('Monthly report late')
    monthly_report = fields.Float('Monthly report')
    punish_arrive_late = fields.Float('Punish arrive late', compute='calculate_total_punish', store=True)
    punish_monthly_report = fields.Float('Punish monthly report', compute='calculate_total_punish', store=True)
    total_punish = fields.Float('Total punish', compute='calculate_total_punish', store=True)
    total_not_bcn = fields.Float('Total not BCN')
    punish_bcn = fields.Float('Punish days BCN')
    punish_bcn_working = fields.Float('Punish working BCN')

    @api.depends('total_arrive_late', 'monthly_report_late', 'monthly_report', 'punish_arrive_late',
                 'punish_monthly_report')
    def calculate_total_punish(self):
        for record in self:
            if record.total_arrive_late:
                record.punish_arrive_late = record.total_arrive_late * 100000
            if record.monthly_report_late or record.monthly_report:
                record.punish_monthly_report = (record.monthly_report_late * 300000) + (record.monthly_report * 1000000)
            record.total_punish = record.punish_arrive_late + record.punish_monthly_report

    def cron_report_timesheet_penalty_calculation(self):
        if date.today().month == 1:
            start_date = date.today().replace(year=date.today().year - 1, month=12, day=1)
        else:
            start_date = date.today().replace(month=date.today().month - 1, day=1)
        end_date = (datetime.now() + relativedelta(day=1, days=-1)).date()
        self.sudo().search(['|', ('start_date', '=', start_date), ('end_date', '=', end_date)]).unlink()
        query = f'''
            select 
                he.id as employee_id, 
                CASE WHEN ual.total_al notnull THEN ual.total_al ELSE 0 end as total_al, 
                CASE WHEN ual.total_al_refuse notnull THEN ual.total_al_refuse ELSE 0 end as total_al_refuse,
                CASE WHEN atten.total_valid_records notnull THEN atten.total_valid_records ELSE 0 end as total_working_day,
                CASE WHEN atten.total_valid_late_records notnull THEN atten.total_valid_late_records ELSE 0 end as total_valid_late_records,
                CASE WHEN analytic_line.total_not_bcn notnull THEN analytic_line.total_not_bcn ELSE 0 end as total_not_bcn
            from hr_employee he 
            left join (
                select employee_id, 
                    SUM(CASE WHEN state = 'validate' THEN 1 ELSE 0 END) AS total_al,
                    SUM(CASE WHEN state != 'validate' THEN 1 ELSE 0 END) AS total_al_refuse
                from arrive_late al 
                where al.date_late >= '{start_date}' and al.date_late < '{end_date}'
                group by employee_id
            ) as ual on ual.employee_id = he.id
            left join (
                select
                    employee_id,
                    SUM(CASE WHEN state = 'validate' THEN 1 ELSE 0 END) AS total_valid_records,
                    SUM(CASE WHEN state = 'validate' AND is_late = true AND arrive_late_id IS NULL THEN 1 ELSE 0 END) AS total_valid_late_records
                FROM
                    hr_attendance ha
                where ha.date_attendance >= '{start_date}' 
                    and ha.date_attendance < '{end_date}'
                group by employee_id 
            ) as atten on atten.employee_id = he.id
            left join (
                select 
                    cta.employee_id, 
                    count(employee_id) as total_not_bcn
                from (
                    select
                        employee_id as employee_id,
                        aal.date
                    from account_analytic_line aal 
                    where aal.date >= '{start_date}' 
                        and aal.date < '{end_date}'
                    group by employee_id, aal.date
                ) as cta
                group by cta.employee_id
            ) as analytic_line on analytic_line.employee_id = he.id;
            '''
        self._cr.execute(query)
        data = self._cr.dictfetchall()
        data_dict = {}
        for item in data:
            item['sum_arrive_late'] = item['total_al_refuse'] + item['total_valid_late_records']
            item['total_arrive_late'] = item['sum_arrive_late'] - 2 if item['sum_arrive_late'] - 2 > 0 else 0
            item['total_not_bcn'] = item['total_working_day'] - item['total_not_bcn'] if item['total_working_day'] - \
                                                                                         item[
                                                                                             'total_not_bcn'] > 0 else 0
            item['punish_bcn'] = item['total_not_bcn'] - 2 if item['total_not_bcn'] - 2 > 0 else 0
            item['punish_bcn_working'] = item['punish_bcn'] * 0.1
            data_dict[item['employee_id']] = item

        query_holidays = f'''
            SELECT date_to, date_from
            FROM resource_calendar_leaves
            WHERE (
                (date_from >= '{start_date}' AND date_from < '{end_date}')
                OR (date_to >= '{start_date}' AND date_to < '{end_date}')
            )
            AND resource_id is null
        '''
        self._cr.execute(query_holidays)
        data_holidays = self._cr.dictfetchall()
        sundays_in_march_2024 = find_sundays(start_date.year, start_date.month)
        total_days = calendar.monthrange(start_date.year, start_date.month)[1]
        total_day = 0
        for rec in data_holidays:
            if rec.get('date_to').date() > end_date:
                for i in range(rec.get('date_from').day, end_date.day + 1):
                    if i not in sundays_in_march_2024['sundays']:
                        total_day += 1
            elif rec.get('date_from').date() < start_date:
                for i in range(start_date.day, rec.get('date_to').day + 1):
                    if i not in sundays_in_march_2024['sundays']:
                        total_day += 1
            else:
                for i in range(rec.get('date_from').day, rec.get('date_to').day + 1):
                    if i not in sundays_in_march_2024['sundays']:
                        total_day += 1

        query_leave = f'''
            SELECT request_date_to as date_to, request_date_from as date_from, employee_id, number_of_days, hlt.requires_allocation
            FROM hr_leave
            JOIN hr_leave_type hlt ON hlt.id = hr_leave.holiday_status_id
            WHERE (
            (request_date_from >= '{start_date}' AND request_date_from < '{end_date}')
            OR (request_date_to >= '{start_date}' AND request_date_to < '{end_date}')
            ) AND state = 'validate' 
        '''
        self._cr.execute(query_leave)
        data_leave = self._cr.dictfetchall()

        vals_list = []
        employee = self.env['hr.employee'].sudo().search([])
        for emp in employee:
            # work_data = {'days': 26.0, 'hours': 181.24999999999997}
            work_data = total_days - len(sundays_in_march_2024['sundays']) - (
                        len(sundays_in_march_2024['saturday']) - 1) / 2
            # work_data = emp._get_work_days_data(start_date, end_date, calendar=emp.contract_id.resource_calendar_id if emp.contract_id else emp.resource_calendar_id)

            total_leave = 0
            for l in data_leave:
                if l.get('employee_id') == emp.id:
                    if l.get('date_to') > end_date:
                        for i in range(l.get('date_from').day, end_date.day + 1):
                            if i in sundays_in_march_2024['saturday']:
                                total_leave += 0.5

                            elif i not in sundays_in_march_2024['sundays']:
                                total_leave += 1
                    elif l.get('date_from') < start_date:
                        for i in range(start_date.day, l.get('date_to').day + 1):
                            if i in sundays_in_march_2024['saturday']:
                                total_leave += 0.5
                            elif i not in sundays_in_march_2024['sundays']:
                                total_leave += 1
                    else:
                        total_leave += l['number_of_days']
            vals = {
                'total_leave': total_leave,
                'standard_working_day': work_data,
                'total_holiday': total_day,
                'total_not_leave': work_data - total_leave - total_day if work_data - total_leave - total_day > 0 else 0,
                'start_date': start_date,
                'end_date': end_date,
            }
            if emp.id in data_dict:
                vals.update(data_dict[emp.id])
                vals['total_not_leave'] = vals['total_not_leave'] - vals['total_working_day'] if vals[
                                                                                                     'total_not_leave'] - \
                                                                                                 vals[
                                                                                                     'total_working_day'] > 0 else 0
                del vals['total_al']
                del vals['total_al_refuse']
                del vals['total_valid_late_records']
                vals_list.append(vals)
        self.sudo().create(vals_list)
