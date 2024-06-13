# -*- coding: utf-8 -*-  

{
    'name': 'Pontusinc CRM',
    'description': 'Pontusinc CRM',
    'summary': '',
    'category': '',
    "sequence": 4,
    'version': '1.0.0',
    'author': 'Duong Trung Hieu',
    'company': 'Pontusinc',
    'website': "",
    'depends': ['crm', 'contacts', 'web', 'base_unit_vn', 'customer_relationship_diagram'],
    'data': [
        'security/ir.model.access.csv',
        'views/res_partner_view.xml',
        'views/res_partner_rank_view.xml',
        'views/res_partner_state_view.xml',
        'views/menu_item.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'pontusinc_crm/static/src/fields/common_one2many.xml',
            'pontusinc_crm/static/src/fields/*',
            'pontusinc_crm/static/src/fields/*.scss',
            'pontusinc_crm/static/src/scss/*.scss',
            'pontusinc_crm/static/src/views/*.js',
            'pontusinc_crm/static/src/xml/**/*',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': True,
}
