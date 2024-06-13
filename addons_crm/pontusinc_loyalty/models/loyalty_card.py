from odoo import fields, models, api, _

class LoyaltyCard(models.Model):
    _name = 'pontusinc.loyalty.card'

    code = fields.Char('Code')
    name = fields.Char('Name')
    partner_id = fields.Many2one('res.partner', string='Partner')
    start_date = fields.Date('Start date')
    end_date = fields.Date('End date')
    create_date_cif = fields.Date('Create date CIF')
    source_id = fields.Many2one('utm.source', string='Source')
    state_kyc = fields.Selection([('kyc', 'KYC'),
                                  ('ekyc', 'EKYC')], string='State EKYC/KYC', default='kyc', required=True)
    price = fields.Float('Price')
    state = fields.Selection([('active', 'Active'), ('inactive', 'Inactive')], string='State', default='active')
    loyalty_type_id = fields.Many2one('loyalty.type', string='Loyalty type')
    rank_id = fields.Many2one('loyalty.rank', string='Rank')




