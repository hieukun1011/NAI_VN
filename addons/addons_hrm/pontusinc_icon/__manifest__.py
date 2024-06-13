# -*- coding: utf-8 -*-  

{
    'name': 'Pontusinc icon',
    'description': 'Change icon all module',
    'summary': '',
    'category': '',
    "sequence": 3,
    'version': '1.0.0',
    'author': 'Duong Trung Hieu',
    'company': 'Company',
    'website': "",
    'depends': ['mail', 'calendar', 'note', 'contacts', 'point_of_sale', 'sale', 'sale_renting', 'account_accountant',
                'marketing_automation', 'mass_mailing', 'mass_mailing_sms', 'event', 'survey', 'purchase', 'stock', 'mrp',
                'maintenance', 'sign', 'hr', 'om_hr_payroll', 'hr_attendance', 'hr_recruitment', 'hr_expense', 'im_livechat',
                'approvals', 'base',],
    'data': [
        'views/menu_item.xml'
    ],

    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}
