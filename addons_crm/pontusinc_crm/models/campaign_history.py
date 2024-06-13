from odoo import fields, models, api, _

class CampaignHistory(models.Model):
    _name = 'campaign.history'
    _rec_name = "code"

    code = fields.Char('Code')
    source_id = fields.Many2one('utm.source', string='Source')
    campaign_id = fields.Many2one('utm.campaign', string='Campaign')
    start_date = fields.Date('Start date')
    end_date = fields.Date('End date')
    partner_id = fields.Many2one('res.partner', string='Partner')
    action_mkt = fields.Char('Action')
    responded = fields.Boolean('Responded', default=False)
    state = fields.Selection([('send', 'Send'), ('outgoing', 'Outgoing')], default='outgoing', string='State')
