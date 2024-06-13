from odoo import fields, models, api


class HrApplicant(models.Model):
    _inherit = 'hr.applicant'

    base_url = fields.Char('URL')
    url_cv = fields.Char('Link CV')
    apply_date = fields.Date('Apply date')
    history_ids = fields.One2many('hr.applicant.history', 'applicant_id', string='History')

    def _get_interviewer_emails(self):
        """ Get comma-separated attendee email addresses. """
        self.ensure_one()
        return ",".join([e.email for e in self.interviewer_ids if e.email])

    def _get_interviewer_name(self):
        """ Get comma-separated attendee email addresses. """
        self.ensure_one()
        name = ''
        for rec in self.interviewer_ids:
            if not name:
                name += rec.name
            else:
                name += ', ' + rec.name
        return name

    @api.model_create_multi
    def create(self, vals_list):
        url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        template = self.env.ref('icomm_recruitment.email_template_data_applicant_new')
        res = super().create(vals_list)
        for record in res:
            if record.interviewer_ids:
                record.base_url = url + '/web#id=%d&view_type=form&model=%s&action=%d' % (
                    record.id, record._name, self.env.ref('hr_recruitment.crm_case_categ0_act_job').id)
                self.env['mail.thread'].message_post_with_template(
                    template.id,
                    res_id=record.id,
                    model=record._name,
                )
        return res

    @api.onchange('job_id')
    def onchange_interviewer_user(self):
        self.ensure_one()
        if self.job_id:
            self.interviewer_ids = self.job_id.interviewer_ids.ids

    def get_company(self):
        self.ensure_one()
        return True if self.company_id.id == self.env.ref('base.main_company') else False

    def action_makeMeeting(self):
        result = super(HrApplicant, self).action_makeMeeting()
        partner_interviewer = []
        if self.interviewer_ids:
            for rec in self.interviewer_ids:
                partner_interviewer.append(rec.partner_id.id)
        result['context']['default_partner_ids'] += partner_interviewer
        return result

    # @api.constrains('stage_id')
    # def notification_state_email(self):
    #     template = self.env.ref('icomm_recruitment.email_template_data_information_applicant_not_scheduled')
    #     for record in self:
    #         if record.user_id and self.env.user.id in record.interviewer_ids.ids and record.base_url \
    #                 and record.stage_id.id == self.env.ref('icomm_recruitment.stage_job_schedule_interview').id:
    #             self.env['mail.thread'].sudo().message_post_with_template(
    #                 template.id,
    #                 res_id=record.id,
    #                 model=record._name,
    #             )
    #         elif record.stage_id.id == self.env.ref('hr_recruitment.stage_job2').id:
    #             template_evaluate_candidate_interviews = self.env.ref(
    #                 'icomm_recruitment.email_template_data_schedule_interview_appointment')
    #             self.env['mail.thread'].sudo().message_post_with_template(
    #                 template_evaluate_candidate_interviews.id,
    #                 res_id=record.id,
    #                 model=record._name,
    #             )
    #         elif record.stage_id.id == self.env.ref('hr_recruitment.stage_job3').id:
    #             template_evaluate_candidate_interviews = self.env.ref(
    #                 'icomm_recruitment.email_template_data_evaluate_candidate_interviews')
    #             self.env['mail.thread'].sudo().message_post_with_template(
    #                 template_evaluate_candidate_interviews.id,
    #                 res_id=record.id,
    #                 model=record._name,
    #             )
    #         elif record.stage_id.id == self.env.ref('hr_recruitment.stage_job4').id:
    #             template_notification_candidates_accepting_jobs = self.env.ref(
    #                 'icomm_recruitment.email_template_data_notification_candidates_accepting_jobs')
    #             self.env['mail.thread'].sudo().message_post_with_template(
    #                 template_notification_candidates_accepting_jobs.id,
    #                 res_id=record.id,
    #                 model=record._name,
    #             )

    def action_archive_applicant(self):
        refuse_reason = self.env['applicant.get.refuse.reason'].sudo().create({
            'applicant_ids': self.ids,
            'refuse_reason_id': self.env.ref('hr_recruitment.refuse_reason_1').id,
            'send_mail': False,
        })
        if refuse_reason:
            refuse_reason.sudo().action_refuse_reason_apply()


class HrJob(models.Model):
    _inherit = 'hr.job'

    base_url = fields.Char('URL')
    count_application_draft = fields.Integer(compute='_compute_application_draft_count',
                                             string='Application draft count')

    @api.depends('application_ids', 'application_ids.stage_id')
    def _compute_application_draft_count(self):
        for record in self:
            count_application_draft = 0
            if record.application_ids:
                for rec in record.application_ids:
                    if rec.stage_id.id == self.env.ref('hr_recruitment.stage_job1').id and not rec.refuse_reason_id:
                        count_application_draft += 1
            record.count_application_draft = count_application_draft

    def _get_interviewer_emails(self):
        """ Get comma-separated attendee email addresses. """
        self.ensure_one()
        return ",".join([e.email for e in self.interviewer_ids if e.email])

    def cron_notification_manager(self):
        url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        template = self.env.ref('icomm_recruitment.email_template_data_notification_manager')
        job = self.search([])
        for record in job:
            if record.user_id and record.interviewer_ids and record.count_application_draft:
                record.base_url = url + '/web#action=hr_recruitment.action_hr_job_applications&active_id=%s' %(record.id)
                self.env['mail.thread'].message_post_with_template(
                    template.id,
                    res_id=record.id,
                    model=record._name,
                )

class HrApplicantHistory(models.Model):
    _name = 'hr.applicant.history'
    _description = 'Hr Applicant History'

    applicant_id = fields.Many2one('hr.applicant', string='Applicant')
    meeting_id = fields.Many2one('calendar.event', string='Meeting')
    attachment_id = fields.Many2many('ir.attachment', 'hr_applicant_history_rel', 'doc_id', 'attach_id4',
                                     string="Attachment", help='You can attach the copy of your Letter')
    start_date = fields.Datetime('Start date', related='meeting_id.start')
    end_date = fields.Datetime('End date', related='meeting_id.stop')
    result = fields.Selection([('fail', 'Fail'), ('wait', 'Wait'), ('pass', 'pass')], string='Result')
    description = fields.Text('Description')
