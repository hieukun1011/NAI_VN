from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo.tools.translate import _
from odoo.addons.base.models.res_partner import _tz_get

class CalendarEvent(models.Model):
    _inherit = 'calendar.event'

    mail_tz = fields.Selection(_tz_get, compute='_compute_mail_tz',
                               help='Timezone used for displaying time in the mail template')
    is_event_company = fields.Boolean('Is event company')
    employee_ids = fields.Many2many('hr.employee.public', string='Employee')
    room_id = fields.Many2one("room.room", string="Room", required=False, ondelete="cascade")

    @api.model_create_multi
    def create(self, vals_list):
        meeting = super(CalendarEvent, self).create(vals_list)
        for record in meeting:
            if record.applicant_id:
                self.env['hr.applicant.history'].sudo().create({
                    'applicant_id': record.applicant_id.id,
                    'meeting_id': record.id
                })
            if record.room_id:
                self.env['room.booking'].sudo().create({
                    'is_event_company': record.is_event_company,
                    'employee_ids': record.employee_ids.ids,
                    'partner_ids': record.partner_ids.ids,
                    'name': record.name,
                    'start_datetime': record.start,
                    'stop_datetime': record.stop,
                    'allday': record.allday,
                    'user_id': record.user_id.id,
                    'description': record.description,
                    'alarm_ids': record.alarm_ids.ids,
                    'location': record.location,
                    'room_id': record.room_id.id,
                    'videocall_location': record.videocall_location,
                    'categ_ids': record.categ_ids.ids,
                    'recurrency': record.recurrency,
                    'privacy': record.privacy,
                    'show_as': record.show_as,
                    'calendar_event_id': record.id,
                    # 'attendee_ids': record.attendee_ids.ids,
                    'create_date': record.create_date,
                })
        return meeting

    def _compute_mail_tz(self):
        for record in self:
            record.mail_tz = record.partner_id.tz

    def action_open_composer(self):
        if self.is_event_company:
            self.partner_ids += self.employee_ids.related_contact_ids
        if not self.partner_ids:
            raise UserError(_("There are no attendees on these events"))
        if self.applicant_id:
            template_id = self.env['ir.model.data']._xmlid_to_res_id('icomm_recruitment.email_template_data_interview_schedule',
                                                                     raise_if_not_found=False)
        else:
            template_id = self.env['ir.model.data']._xmlid_to_res_id('calendar.calendar_template_meeting_update',
                                                                 raise_if_not_found=False)
        # The mail is sent with datetime corresponding to the sending user TZ
        composition_mode = self.env.context.get('composition_mode', 'comment')
        compose_ctx = dict(
            default_composition_mode=composition_mode,
            default_model='calendar.event',
            default_res_ids=self.ids,
            default_use_template=bool(template_id),
            default_template_id=template_id,
            default_partner_ids=self.partner_ids.ids,
            mail_tz=self.env.user.tz,
        )
        return {
            'type': 'ir.actions.act_window',
            'name': _('Contact Attendees'),
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(False, 'form')],
            'view_id': False,
            'target': 'new',
            'context': compose_ctx,
        }
