# -*- coding: utf-8 -*-
{
    'name': "Zalo Configuration",
    'summary': "Zalo Configuration",
    'description': "Zalo Configuration",
    'author': "G-ERP",
    'website':'erptoancau.com',
    # for the full list
    'version': '17.0.0.2',

    # any module necessary for this one to work correctly
    'depends': [
        'base',
        'contacts',
    ],
    'currency': 'USD',
    'price': 250,
    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/data.xml',
        'views/zalo_configuration_views.xml',
    ],
    'license': 'OPL-1',
    'application': True,
    'installable': True,
}
