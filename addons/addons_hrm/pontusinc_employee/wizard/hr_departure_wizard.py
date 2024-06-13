# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrDepartureWizard(models.TransientModel):
    _inherit = 'hr.departure.wizard'

    def _get_emails_hr_attendance(self):
        """ Get comma-separated attendee email addresses. """
        self.ensure_one()
        hr_user = self.env['res.users'].sudo().search([('groups_id', 'in', self.env.ref('to_attendance_device.group_attendance_devices_manager').id)])
        return ",".join([e.email for e in hr_user.sudo() if e.email])

    def action_register_departure(self):
        super().action_register_departure()
        mail_template = self.env.ref('pontusinc_employee.email_template_data_notification_delete_fingerprint')
        self.env['mail.thread'].message_post_with_template(
            mail_template.id,
            res_id=self.id,
            model=self._name,
        )

