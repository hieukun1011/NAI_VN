# -*- coding: utf-8 -*- 
###################################################################################
from odoo import models, fields, api, _


class HrCustody(models.Model):
    _inherit = 'hr.employee'

    custody_count = fields.Integer(compute='_custody_count', string='# Custody')

    # count of all custody contracts
    def _custody_count(self):
        for each in self:
            custody_ids = self.env['hr.device.main'].search([('employee_id', '=', each.id)])
            each.custody_count = len(custody_ids)

    # smart button action for returning the view of all custody contracts related to the current employee
    def custody_view(self):
        for each1 in self:
            value = {
                'domain': str([('employee_id', '=', each1.id)]),
                'view_mode': 'tree,form',
                'res_model': 'hr.device.main',
                'view_id': False,
                'type': 'ir.actions.act_window',
                'name': _('Vật tư/Thiết bị'),
                'context': {}
            }
            return value
