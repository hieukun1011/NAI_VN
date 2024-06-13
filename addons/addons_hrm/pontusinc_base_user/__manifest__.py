# -*- coding: utf-8 -*-  

{
    'name': 'Pontusinc Base User',
    'description': 'Pontusinc Base User',
    'summary': '',
    'category': '',
    "sequence": 3,
    'version': '1.0.0',
    'author': 'Duong Trung Hieu',
    'company': 'Company',
    'website': "",
    'depends': ['base', 'auth_signup'],
    'data': [
        'data/mail_template_data.xml',
        'views/res_users_view.xml',
    ],

    'installable': True,
    'auto_install': True,
    'application': False,
    'license': 'LGPL-3',
}
