# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class DeviceChange(models.TransientModel):
    _name = 'device.change'

    emp_id = fields.Many2one('hr.employee', string='Người phụ trách')
    date_change = fields.Date('Ngày bàn giao', default=fields.Datetime.now())
    reason_change = fields.Text('Lý do')
    dep_id = fields.Many2one('hr.department', 'Phòng ban sử dụng', tracking=True)
    parent_id = fields.Many2one('hr.employee', 'Quản lý', readonly=1)
    location = fields.Char('Sử dụng ở vị trí')

    @api.model
    def default_get(self, fields):
        res = super(DeviceChange, self).default_get(fields)
        device_id = self.env.context.get('active_id')
        device = self.env['hr.device.main'].browse(device_id)
        if 'dep_id' in fields:
            res.update({'dep_id': device.department_id})
        return res

    @api.onchange('dep_id')
    def _onchange_department(self):
        self.parent_id = self.dep_id.manager_id

    def modify(self):
        """ Modifies the duration of asset for calculating depreciation
        and maintains the history of old values, in the chatter.
        """
        device_id = self.env.context.get('active_id', False)
        device = self.env['hr.device.main'].browse(device_id)
        device_vals = {
            'employee_id': self.emp_id,
            'department_id': self.dep_id,
            'date_change': self.date_change,
            'reason_change': self.reason_change,
            'location': self.location,
            'parent_id': self.parent_id,
        }
        if self.emp_id == device.employee_id:
            raise ValidationError("Người phụ trách không thể trùng")
        device.write(device_vals)
        return {'type': 'ir.actions.act_window_close'}
