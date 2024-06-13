import calendar
from datetime import date, datetime

from odoo import fields, models

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


MONTH_SELECTION = [
    ('1', 'January'),
    ('2', 'February'),
    ('3', 'March'),
    ('4', 'April'),
    ('5', 'May'),
    ('6', 'June'),
    ('7', 'July'),
    ('8', 'August'),
    ('9', 'September'),
    ('10', 'October'),
    ('11', 'November'),
    ('12', 'December'),
]


class PopupReportTimesheet(models.TransientModel):
    _name = 'popup.report.timesheet'

    month = fields.Selection(MONTH_SELECTION, string='Months', required=True)

    def cron_report_timesheet_penalty_calculation(self):
        start_date = datetime.now().replace(month=int(self.month), day=1)
        end_date = datetime.now().replace(month=int(self.month) + 1, day=1)
        query = f'''
            select 
                he.id as employee_id, 
                ual.total_al, 
                ual.total_al_refuse, 
                atten.total_valid_records as total_working_day, 
                atten.total_valid_late_records
            from hr_employee he 
            join (
                select employee_id, 
                    SUM(CASE WHEN state = 'validate' THEN 1 ELSE 0 END) AS total_al,
                    SUM(CASE WHEN state != 'validate' THEN 1 ELSE 0 END) AS total_al_refuse
                from arrive_late al 
                where al.date_late >= '{start_date}' and al.date_late < '{end_date}'
                group by employee_id
            ) as ual on ual.employee_id = he.id
            join (
                select
                    employee_id,
                    SUM(CASE WHEN state = 'validate' THEN 1 ELSE 0 END) AS total_valid_records,
                    SUM(CASE WHEN state = 'validate' AND is_late = true AND arrive_late_id IS NULL THEN 1 ELSE 0 END) AS total_valid_late_records
                FROM
                    hr_attendance ha
                where ha.date_attendance >= '{start_date}' 
                    and ha.date_attendance < '{end_date}'
                group by employee_id 
            ) as atten on atten.employee_id = he.id;
            '''
        self._cr.execute(query)
        data = self._cr.dictfetchall()
        data_dict = {}
        for item in data:
            item['sum_arrive_late'] = item['total_al_refuse'] + item['total_valid_late_records']
            item['total_arrive_late'] = item['sum_arrive_late'] - 2 if item['sum_arrive_late'] - 2 > 0 else 0
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
            if rec.get('date_to') > end_date:
                for i in range(rec.get('date_from').day, end_date.day + 1):
                    if i not in sundays_in_march_2024['sundays']:
                        total_day += 1
            elif rec.get('date_from') < start_date:
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
                    if l.get('date_to') > end_date.date():
                        for i in range(l.get('date_from').day, end_date.day + 1):
                            if i in sundays_in_march_2024['saturday']:
                                total_leave += 0.5

                            elif i not in sundays_in_march_2024['sundays']:
                                total_leave += 1
                    elif l.get('date_from') < start_date.date():
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
                'total_not_leave': work_data - total_leave,
                'start_date': start_date,
                'end_date': end_date,
            }
            if emp.id in data_dict:
                vals.update(data_dict[emp.id])
                vals['total_not_leave'] = vals['total_not_leave'] - vals['total_working_day']
                del vals['total_al']
                del vals['total_al_refuse']
                del vals['total_valid_late_records']
                vals_list.append(vals)
        self.env['timesheet.penalty.calculation'].sudo().create(vals_list)
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
