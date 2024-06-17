# -*- coding: utf-8 -*-  

{
    'name': 'Pontusinc POS',
    'description': 'Pontusinc POS',
    'summary': '',
    'category': '',
    "sequence": 3,
    'version': '1.0.0',
    'author': 'Duong Trung Hieu',
    'company': 'Company',
    'website': "",
    'depends': ['point_of_sale'],
    'data': [
        'views/pos_assets_index.xml',
        'views/pos_view_kanban.xml'
    ],
    'assets': {
        'point_of_sale.assets': [
            # 'pontusinc_pos/static/src/xml/Chrome.xml',
            'pontusinc_pos/static/src/scss/pos.scss',
        ],
        'point_of_sale._assets_pos': [
            'pontusinc_pos/static/src/**/*',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': False,
}
