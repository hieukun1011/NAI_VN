# -*- coding: utf-8 -*-  

{
    'name': 'Pontusinc employee',
    'description': 'Pontusinc customize employee',
    'summary': '',
    'category': '',
    "sequence": 3,
    'version': '1.0.0',
    'author': 'Duong Trung Hieu',
    'company': 'Company',
    'website': "",
    'depends': ['hr', 'to_attendance_device'],
    'data': [
        'data/mail_template_data.xml',
        'data/ir_sequence_data.xml',
        'views/hr_employee_view.xml',
        'views/pontusinc_hr_department_view.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css',
            'pontusinc_employee/static/src/js/insert_face.js',
            'pontusinc_employee/static/src/css/style.css',
            'pontusinc_employee/static/src/xml/insert_face_employee.xml',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}
