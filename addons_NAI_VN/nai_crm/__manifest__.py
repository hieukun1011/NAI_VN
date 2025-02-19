# Copyright 2024 Wokwy - quochuy.software@gmail.com
{
    'name': 'NAI CRM',
    'version': '1.0',
    'category': 'CRM',
    'summary': '',
    'author': '',
    'website': '',
    'depends': ['base', 'sale', 'sale_renting'],
    'data': [
        'security/module_security.xml',
        'security/ir.model.access.csv',
        'wizard/popup_select_fields_report_view.xml',
        'views/nai_product_template_view.xml',
        'views/nai_sale_order_view.xml',
        'report/custom_report_sale_order.xml',
        'data/nai_attrs_product_data.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'translations': ['i18n/vi_VN.po'],
}