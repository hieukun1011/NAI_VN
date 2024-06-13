# -*- coding: utf-8 -*-  

{
    'name': 'Pontusinc holidays',
    'description': 'Pontusinc holidays',
    'summary': '',
    'category': '',
    "sequence": 3,
    'version': '1.0.0',
    'author': 'Duong Trung Hieu',
    'company': 'Company',
    'website': "",
    'depends': ['hr_holidays', 'resource', 'hr_holidays_attendance', 'to_attendance_device'],
    'data': [
        'security/module_security.xml',
        'security/ir.model.access.csv',
        'data/cron_report_timesheet_penalty.xml',
        'data/qweb_mail_holidays_inherit.xml',
        'views/hr_employee_views.xml',
        'views/hr_holidays_views.xml',
        'views/hr_leave_type_views.xml',
        'views/hr_leave_accrual_plan_level.xml',
        'views/hr_leave_view.xml',
        'report/report_timesheet_penalty_calculation_view.xml',
        'wizard/popup_report_timesheet_view.xml',
        'views/menu_item.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'pontusinc_holidays/static/src/views/*',
            'pontusinc_holidays/static/src/js/calendar_controller_inherit.js',
            'pontusinc_holidays/static/src/js/calendar_controller_inherit_view.xml',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'LGPL-3',
}
