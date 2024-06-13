# -*- coding: utf-8 -*-  

{
    'name': 'ICOMM Recruitment',
    'description': 'ICOMM Recruitment',
    'summary': '',
    'category': '',
    "sequence": 3,
    'version': '1.0.0',
    'author': 'Duong Trung Hieu',
    'company': 'Company',
    'website': "",
    'depends': ['hr_recruitment', 'web', 'calendar'],
    'data': [
        'security/ir.model.access.csv',
        'data/data_attachment.xml',
        'data/mail_template_data.xml',
        'data/ir_cron_data.xml',
        'data/data_stage_applicant.xml',

        'views/icomm_recruitment_views.xml',
        'views/hr_employee_view.xml',
        'views/calendar_event_view.xml',
        'views/view_res_partner.xml',
        'views/webclient_templates.xml',
    ],
    'assets': {
            'web.assets_backend': [
                'icomm_recruitment/static/scss/view.scss',
                'icomm_recruitment/static/src/webclient.js'
            ],
        },
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}
