from datetime import datetime

from odoo import fields, models, api, _


class PopupRewards(models.TransientModel):
    _name = 'popup.rewards'
    _description = 'Open popup reward'

    name = fields.Char('Name', translate=True)
    rank_id = fields.Many2one('loyalty.rank', string='Rank')
    score = fields.Integer('Score')
    quantity = fields.Float('Quantity')
    expiration_date = fields.Date('Expiration date')
    program_id = fields.Many2one('loyalty.program', string='Program')
    loyalty_id = fields.Many2one('loyalty.customer', string='Loyalty')
    code = fields.Char('Code')
    type = fields.Selection([('reward', 'Reward'), ('discount', 'Discount'), ('rank', 'Rank')], string='Type')
    is_activated = fields.Boolean(default=lambda self: self.env.context.get('change_state_activated'))
    is_exclude = fields.Boolean(default=lambda self: self.env.context.get('change_state_exclude'))

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        if res.is_activated:
            res.loyalty_id.state = 'activated'
        elif res.is_exclude:
            res.loyalty_id.state = 'exclude'
        elif res.score and res.type == 'reward':
            res.loyalty_id.score += res.score
            vals_list = [{
                'accumulate_points': res.score,
                'expires_date': res.expiration_date,
                'note': res.name,
                'member_id': res.loyalty_id.id,
            }]
            res.loyalty_id.with_context(log_change_score=True).create_log(vals_list)
        elif res.type == 'rank' and res.rank_id:
            res.loyalty_id.rank_id = res.rank_id
            vals_list = [{
                'rank_id': res.rank_id.id,
                'state_rank': 'up_rank',
                'start_date': datetime.now(),
                'stop_date': res.expiration_date,
                'member_id': res.loyalty_id.id,
            }]
            res.loyalty_id.with_context(log_change_rank=True).create_log(vals_list)
        return res


    def _get_attendee_emails(self):
        """ Get comma-separated attendee email addresses. """
        self.ensure_one()
        return ",".join([e for e in self.loyalty_id.partner_id.ids if e])

    def send_mail(self):
        if self.env.context.get('change_state_activated'):
            mail_template = self.env.ref('pontusinc_loyalty.email_template_data_activated_card')
            self.env['mail.thread'].message_post_with_template(
                mail_template.id,
                res_id=self.id,
                model=self._name,
            )
        elif self.env.context.get('change_state_exclude'):
            mail_template = self.env.ref('pontusinc_loyalty.email_template_data_exclude_card')
            self.env['mail.thread'].message_post_with_template(
                mail_template.id,
                res_id=self.id,
                model=self._name,
            )
        elif self.score and self.type == 'reward':
            mail_template = self.env.ref('pontusinc_loyalty.email_template_data_donate_score')
            self.env['mail.thread'].message_post_with_template(
                mail_template.id,
                res_id=self.id,
                model=self._name,
            )
        elif self.type == 'rank' and self.rank_id:
            mail_template = self.env.ref('pontusinc_loyalty.email_template_data_up_rank')
            self.env['mail.thread'].message_post_with_template(
                mail_template.id,
                res_id=self.id,
                model=self._name,
            )
        else:
            template_id = self.env['ir.model.data']._xmlid_to_res_id('calendar.calendar_template_meeting_update',
                                                                     raise_if_not_found=False)
            # The mail is sent with datetime corresponding to the sending user TZ
            composition_mode = self.env.context.get('composition_mode', 'comment')
            compose_ctx = dict(
                default_composition_mode=composition_mode,
                default_model='loyalty.customer',
                default_res_ids=self.loyalty_id.ids,
                default_use_template=bool(template_id),
                default_template_id=template_id,
                default_partner_ids=self.loyalty_id.partner_id.ids,
                mail_tz=self.env.user.tz,
            )
            return {
                'type': 'ir.actions.act_window',
                'name': _('Send mail'),
                'view_mode': 'form',
                'res_model': 'mail.compose.message',
                'views': [(False, 'form')],
                'view_id': False,
                'target': 'new',
                'context': compose_ctx,
            }

    @api.model
    def default_get(self, default_fields):
        vals = super(PopupRewards, self).default_get(default_fields)
        vals['type'] = vals.get('type', self.env.context.get('default_type'))
        return vals
