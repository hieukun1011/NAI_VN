# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class MaintenanceChangePersonInCharge(models.TransientModel):
    _name = 'maintenance.request.change'

    emp_id = fields.Many2one('hr.employee', string='Người phụ trách')
    reason_change = fields.Text('Lí do thay đổi')

    @api.model
    def default_get(self, fields):
        res = super(MaintenanceChangePersonInCharge, self).default_get(fields)
        maintenance_id = self.env.context.get('active_id')
        maintenance = self.env['hr.maintenance.request'].browse(maintenance_id)
        if 'emp_id' in fields:
            res.update({'emp_id': maintenance.emp_id})
        return res

    def modify(self):
        """ Modifies the duration of asset for calculating depreciation
        and maintains the history of old values, in the chatter.
        """
        maintenance_id = self.env.context.get('active_id', False)
        maintenance = self.env['hr.maintenance.request'].browse(maintenance_id)
        maintenance_vals = {
            'emp_id': self.emp_id,
            'reason_change': self.reason_change,
        }
        if self.emp_id == maintenance.emp_id:
            raise ValidationError("Người phụ trách không thể trùng")
        maintenance.write(maintenance_vals)
        return {'type': 'ir.actions.act_window_close'}
