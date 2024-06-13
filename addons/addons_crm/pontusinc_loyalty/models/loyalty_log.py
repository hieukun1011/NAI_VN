from odoo import fields, models, api


class LoyaltyLogChangeScore(models.Model):
    _name = 'loyalty.log.change.score'
    _description = 'Loyalty save log change score'

    accumulate_points = fields.Float('Accumulate points')
    minus_points = fields.Float('Minus points')
    expires_points = fields.Float('Expires')
    expires_date = fields.Date('Expires date')
    note = fields.Text('Note')
    order_id = fields.Many2one('sale.order', string='Code')
    program_id = fields.Many2one('loyalty.program')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    member_id = fields.Many2one('loyalty.customer', string='Member')
    payment_method_line_id = fields.Many2one('account.payment.method.line', string='Payment Method')

class LoyaltyLogChangeRank(models.Model):
    _name = 'loyalty.log.change.rank'
    _description = 'Loyalty save log change rank'

    rank_id = fields.Many2one('loyalty.rank', string='Rank')
    start_date = fields.Datetime('Start date')
    stop_date = fields.Datetime('Stop date')
    reason_id = fields.Many2one('loyalty.reason.rank', string='Reason')
    program_ids = fields.Many2many('loyalty.program', string='Program')
    note = fields.Text('Note')
    member_id = fields.Many2one('loyalty.customer', string='Member')
    state_rank = fields.Selection([('up_rank', 'Up Rank'), ('down_rank', 'Down Rank'), ('keep_rank', 'Keep rank')],
                                  string='State')


class LoyaltyReasonRank(models.Model):
    _name = 'loyalty.reason.rank'
    _description = 'Reason for changing membership class'

    name = fields.Char('Name')
