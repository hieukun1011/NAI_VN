from odoo import fields, models, api


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


class LoyaltyCard(models.Model):
    _inherit = 'loyalty.card'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('partner_id'):
                loyalty_card = self.env['loyalty.customer'].sudo().search([('partner_id', '=', vals.get('partner_id'))],
                                                                          limit=1)
                if loyalty_card:
                    loyalty_card.write({
                        'score': vals.get('points')
                    })
                else:
                    self.env['loyalty.customer'].sudo().create([{
                        'partner_id': vals.get('partner_id'),
                        'score': vals.get('points')
                    }])
        res = super().create(vals_list)
        return res

    def write(self, vals):
        if vals.get('points'):
            loyalty_card = self.env['loyalty.customer'].sudo().search([('partner_id', '=', self.partner_id.id)],
                                                                      limit=1)
            if loyalty_card:
                loyalty_card.write({
                    'score': vals.get('points')
                })
            else:
                self.env['loyalty.customer'].sudo().create([{
                    'partner_id': vals.get('partner_id'),
                    'score': vals.get('points')
                }])
        res = super().write(vals)
        return res
