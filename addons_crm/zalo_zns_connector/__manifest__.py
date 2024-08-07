# -*- coding: utf-8 -*-
# =====================================================================================
# License: OPL-1 (Odoo Proprietary License v1.0)
#
# By using or downloading this module, you agree not to make modifications that
# affect sending messages through erptoancau.com or avoiding contract a Plan with erptoancau.com.
# Support our work and allow us to keep improving this module and the service!

# =====================================================================================
# -*- coding: utf-8 -*-
{
    'name': "ZNS Zalo",

    'summary': """
        Connect ZNS Zalo""",

    'description': """
    """,

    'author': "G-ERP",
    'website': "https://erptoancau.com",
    'category': 'Tools',
    'version': '17.0.0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'mail', 'zalo_configuration'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/cron.xml',

        # 'wizard/zns_wizard_view.xml',

        'views/mail_template_view.xml',
        'views/mail_mail_view.xml',

        'views/menu.xml',
    ],
    'images': ['static/description/banner.png'],
    'currency': 'USD',
    'price': 140,
}
