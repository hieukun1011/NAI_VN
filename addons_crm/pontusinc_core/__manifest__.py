# -*- coding: utf-8 -*-  

{
    'name': 'Pontusinc Core',
    'description': 'ICOMM Recruitment',
    'summary': '',
    'category': '',
    "sequence": 3,
    'version': '1.0.0',
    'author': 'Duong Trung Hieu',
    'company': 'Company',
    'website': "",
    'depends': ['web', 'base_import', 'pontusinc_crm'],
    'data': [
        'security/ir.model.access.csv',
        'views/webclient_templates.xml',
        'views/res_config_settings.xml',
    ],
    'assets': {
            'web.assets_backend': [
                'pontusinc_core/static/scss/view.scss',
                'pontusinc_core/static/src/webclient.js',
                'pontusinc_core/static/src/xml/base_import.xml',
                'pontusinc_core/static/src/dialog/dialog.js',
                'pontusinc_core/static/src/search/search_bar.js',
                'pontusinc_core/static/src/notification_alert/notification_alert.xml',
            ],
        },
    'installable': True,
    'auto_install': True,
    'application': False,
}
