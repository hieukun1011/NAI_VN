from odoo import fields, models, api, _

class RankPartner(models.Model):
    _name = 'rank.partner'

    name = fields.Char('name')
    level_ids = fields.Many2many('partner.level', string='Level')

class RankLevel(models.Model):
    _name = 'rank.level'

    name = fields.Char('Level')

class PartnerRankHistory(models.Model):
    _name = 'partner.rank.history'

    partner_id = fields.Many2one('res.partner', string='Partner')
    rank_id = fields.Many2one('rank.partner', string='Rank partner')
    level_id = fields.Many2one('rank.level', string='Level rank')
    start = fields.Date('Start')
    stop = fields.Date('Stop')
    is_expected = fields.Boolean('Is expected')