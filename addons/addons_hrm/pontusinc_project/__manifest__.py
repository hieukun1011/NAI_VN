# -*- coding: utf-8 -*-  

{
    'name': 'Pontusinc Project',
    'description': 'Pontusinc Project',
    'summary': '',
    'category': '',
    "sequence": 3,
    'version': '1.0.0',
    'author': 'Duong Trung Hieu',
    'company': 'Pontusinc',
    'website': "",
    'depends': ['project', 'hr_timesheet', 'jwt_provider', 'pontusinc_employee'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/cron_sync_asana.xml',
        'data/project_task_type_data.xml',
        'data/project_data.xml',
        'views/project_task_view.xml',
        'views/project_view.xml',
        'views/hr_timesheet_view.xml',
        'views/project_task_type_view.xml',
        'views/log_state_task.xml',
        'views/project_backlog_views.xml',
        'report/report_bcn.xml',
        'views/menu_action_view.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'pontusinc_project/static/src/js/many2one_project_redirect.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'LGPL-3',
}
