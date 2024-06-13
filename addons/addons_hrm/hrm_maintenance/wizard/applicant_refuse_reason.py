# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class MaintenanceGetRefuseReason(models.TransientModel):
    _name = 'maintenance.request.get.result'
    _description = 'Maintenance Request Get Refuse Reason'

    result_id = fields.Many2one('maintenance.request.reason', 'Chọn phản hồi')
    maintenance_ids = fields.Many2many('hr.maintenance.request')
    send_mail = fields.Boolean("Send Email", compute='_compute_send_mail', store=True, readonly=False)
    template_id = fields.Many2one('mail.template', string='Email Template',
        compute='_compute_send_mail', store=True, readonly=False,
        domain="[('model', '=', 'hr.maintenance.request')]")
    maintenance_without_email = fields.Text(compute='_compute_maintenance_request_without_email',
        string='Applicant(s) not having email')

    @api.depends('result_id')
    def _compute_send_mail(self):
        for wizard in self:
            template = wizard.result_id.template_id
            wizard.send_mail = bool(template)
            wizard.template_id = template

    @api.depends('maintenance_ids', 'send_mail')
    def _compute_maintenance_request_without_email(self):
        for wizard in self:
            maintenance = wizard.maintenance_ids.filtered(lambda x: not x.email and not x.person_name.user_partner_id.email)
            if maintenance and wizard.send_mail:
                wizard.maintenance_without_email =  (
                    _("The email will not be sent to the requester(s) because they do not have an email address."),

                )
            else:
                wizard.maintenance_without_email = False

    def action_reason_maintenance_request(self):
        if self.send_mail:
            close_date = fields.Datetime.now()
            completion_time = (close_date - self.maintenance_ids.request_date)

            if not self.template_id:
                raise UserError(_("Email template must be selected to send a mail"))
            if not self.maintenance_ids.filtered(lambda x: x.email or x.person_name.user_partner_id.email):
                raise UserError(_("Email of the applicant is not set, email won't be sent."))
            if self.result_id.id == 1:
                self.maintenance_ids.write({'result_id': self.result_id, 'state': 'done', 'close_date': close_date,
                                            'completion_time': completion_time
                                            })
            elif self.result_id.id == 2:
                self.maintenance_ids.write({'result_id': self.result_id, 'state': 'cancel', 'close_date': close_date,
                                            'completion_time': completion_time})
        if self.send_mail:
            main = self.maintenance_ids
            self.env['mail.thread'].message_post_with_template(
                self.template_id.id,
                res_id=main.id,
                model=main._name,
            )
