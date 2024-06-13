# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Customer relationship diagram',
    'category': 'Hidden',
    'version': '1.0',
    'description':
        """
Org Chart Widget for HR
=======================

This module extend the employee form with a organizational chart.
(N+1, N+2, direct subordinates)
        """,
    'depends': ['hr', 'web'],
    'auto_install': True,
    'data': [
        # 'views/res_partner_view.xml'
    ],
    'assets': {
        'web._assets_primary_variables': [
            'customer_relationship_diagram/static/src/scss/variables.scss',
        ],
        'web.assets_backend': [
            'customer_relationship_diagram/static/src/fields/*',
        ],
    },
    'license': 'LGPL-3',
}
