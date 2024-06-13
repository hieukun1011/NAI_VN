from odoo import fields, models, api, _

STATE_KYC = [('kyc', 'KYC'), ('ekyc', 'EKYC')]

class CustomerCard(models.Model):
    _name = 'customer.card'

    name = fields.Char('CIF')
    source_id = fields.Many2one('utm.source', string='Source')
    state = fields.Selection(STATE_KYC, string='State')
    start_date = fields.Date('Start date')
    stop_date = fields.Date('Stop date')

