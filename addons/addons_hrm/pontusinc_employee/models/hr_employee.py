from odoo import fields, models, api, _
import requests
import json

from odoo.exceptions import ValidationError

URL = 'http://14.232.208.130:7895'

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    have_face = fields.Boolean('Have face', default=False)
    is_check_barcode = fields.Boolean(default=False)

    _sql_constraints = [
        ('barcode_unique', 'UNIQUE (barcode)', 'Barcode must be unique!'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('barcode'):
                vals['barcode'] = self.env['ir.sequence'].next_by_code('timekeeping.code') or 'TKC'
        res = super(HrEmployee, self).create(vals_list)
        return res

    def create_employee_camera_checkin(self):
        self.ensure_one()
        if self.barcode:
            url = URL + '/api/camckin/v1/insert/user_hrm'
            template = {
                "email": self.work_email,
                "last_name": self.name.split(' ')[0],
                "first_name": self.name.split(' ')[1:],
                "phone": self.mobile_phone or self.phone or self.work_phone or False,
                "user_code": self.barcode,
            }
            session = requests.Session()
            response = session.post(url, data=json.dumps(template))
            data = response.json()  # Dữ liệu trả về từ API
            if response.status_code == 200:
                self.have_face = True
                return data
            else:
                raise ValidationError(_("Server error"))

    def insert_user_camera_checkin(self):
        self.ensure_one()
        return {
            'name': 'Insert user camera checkin',
            'type': 'ir.actions.client',
            'tag': 'insert_face_cam_checkin',
            'target': 'new',
            'params': {
                'record_id': self.id,
            }
        }

    def action_post_facedetection_icommface(self, base64_faces=False):
        self.ensure_one()
        url = URL + '/api/camckin/v1/face-detection-bs64'
        params = {
            'name': self.name
        }
        template = {
            'base64': base64_faces
        }
        session = requests.Session()
        response = session.post(url, data=json.dumps(template), params=params)
        data = response.json()  # Dữ liệu trả về từ API
        if response.status_code == 200:
            return data
        else:
            raise ValidationError(_("Server error"))

    def action_insert_user_face_hrm(self, value):
        self.ensure_one()
        url = URL + '/api/camckin/v1/insert/user_face_hrm'
        template = {
            "user_code": '503',
            "lst_base64": value['res']['base64_faces'],
            "lst_face_align": str(value['res']['face_align']),
            "scores_penalty": [
                1
            ]
        }
        session = requests.Session()
        response = session.post(url, data=json.dumps(template))
        data = response.json()  # Dữ liệu trả về từ API
        if response.status_code == 200:
            return {'type': 'ir.actions.act_window_close'}
        else:
            raise ValidationError(_("Server error"))

class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    have_face = fields.Boolean('Have face', default=False)
    is_check_barcode = fields.Boolean(default=False)