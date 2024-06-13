# -*- coding: utf-8 -*-
{
    "name": "Vietnam - Base Unit",
    "version": "2.0",
    'summary': 'Customize by Chí Nguyễn',
    'category': 'Localization',
    "depends": [
        "l10n_vn",
        "base",
        "contacts",
    ],
    "data": [
        'security/ir.model.access.csv',
        'data/res.country.district.csv',
        'data/res.country.ward.csv',
        'views/res_country_district_view.xml',
        'views/res_country_ward_view.xml',
        'views/nation_view.xml',
        # 'views/menu_action.xml',
    ],
}
