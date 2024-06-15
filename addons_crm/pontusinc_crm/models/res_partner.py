from odoo import fields, models, api, _
from itertools import groupby
from operator import itemgetter

TYPEINFO = [('cccd', 'CCCD'), ('cmnd', 'CMND'), ('passport', 'Passport')]
RELATIONSHIP = [('mother', 'Mother'),
                ('father', 'Father'),
                ('brother', 'Brother'),
                ('husband', 'Husband'),
                ('wife', 'Wife')]


class PontusincPartner(models.Model):
    _inherit = 'res.partner'

    company_type = fields.Selection(selection_add=[('bank', 'Bank')])
    is_bank = fields.Boolean('Is bank')
    presenter_id = fields.Many2one('res.partner', string='Presenter')
    type_info = fields.Selection(TYPEINFO, 'Type info', required=True, tracking=True, default='cccd')
    relationship = fields.Selection(RELATIONSHIP, 'Relationship')
    identification_code = fields.Char('Identification code', tracking=True)
    expiration_date = fields.Date('Expiration date')
    stage_id = fields.Many2one('res.partner.state', string='State')
    history_rank_ids = fields.One2many('partner.rank.history', 'partner_id', string='Partner rank history')
    expected_rank_id = fields.Many2one('partner.rank.history', string='Expected rank')
    birthday = fields.Date('Birthday')
    district_id = fields.Many2one('res.country.district', string='District')
    ward_id = fields.Many2one('res.country.ward', string='Ward')
    hometown_city_id = fields.Many2one('res.country.state', string='Homeland city')
    hometown_district_id = fields.Many2one('res.country.district', string='Homeland District')
    hometown_ward_id = fields.Many2one('res.country.ward', string='Homeland ward')
    hometown_address = fields.Char('Homeland address')
    emergency_contact_id = fields.Many2one('res.partner', string='Emergency contact')
    impact_level = fields.Char('Impact level')
    asset = fields.Char('Asset')
    average_income = fields.Float('Average income')
    spending_diary_ids = fields.One2many('spending.diary', 'partner_id', string='Spending diary')
    interactive_diary_ids = fields.One2many('interactive.diary', 'partner_id', string='Interactive diary')
    campaign_history_ids = fields.One2many('campaign.history', 'partner_id', string='Campaign history')
    child_presenter_ids = fields.One2many('res.partner', 'presenter_id', string='Child')
    search_profiling = fields.Char('Search profiling', tracking=True)
    child_all_count = fields.Integer(
        'Indirect Subordinates Count',
        compute='_compute_subordinates', recursive=True, store=False,
        compute_sudo=True)
    subordinate_ids = fields.One2many('res.partner', string='Subordinates', compute='_compute_subordinates',
                                      help="Direct and indirect subordinates",
                                      compute_sudo=True)
    facebook_id = fields.Char('Facebook ID')
    company_name = fields.Char('Company Name')
    school_name = fields.Char('School Name')
    province = fields.Char('Province')
    hometown = fields.Char('Hometown')
    checkin_location = fields.Char('Checkin location')

    def _get_subordinates(self, parents=None):
        """
        Helper function to compute subordinates_ids.
        Get all subordinates (direct and indirect) of an employee.
        An employee can be a manager of his own manager (recursive hierarchy; e.g. the CEO is manager of everyone but is also
        member of the RD department, managed by the CTO itself managed by the CEO).
        In that case, the manager in not counted as a subordinate if it's in the 'parents' set.
        """
        if not parents:
            parents = self.env[self._name]

        indirect_subordinates = self.env[self._name]
        parents |= self
        direct_subordinates = self.child_presenter_ids - parents
        child_subordinates = direct_subordinates._get_subordinates(
            parents=parents) if direct_subordinates else self.browse()
        indirect_subordinates |= child_subordinates
        return indirect_subordinates | direct_subordinates

    @api.depends('child_presenter_ids', 'child_presenter_ids.child_all_count')
    def _compute_subordinates(self):
        for partner in self:
            partner.subordinate_ids = partner._get_subordinates()
            partner.child_all_count = len(partner.subordinate_ids)

    @api.onchange('company_type')
    def onchange_company_type(self):
        self.write({
            'is_company': (self.company_type == 'company'),
            'is_bank': (self.company_type == 'bank')
        })

    def test(self):
        print('_')

    @api.depends('is_company', 'is_bank')
    def _compute_company_type(self):
        for partner in self:
            if partner.is_company:
                partner.company_type = 'company'
            elif partner.is_bank:
                partner.company_type = 'bank'
            else:
                partner.company_type = 'person'

    @api.model_create_multi
    def create(self, vals_list):
        counts = {}
        for vals in vals_list:
            phone = vals.get("phone")
            counts[phone] = counts.get(phone, 0) + 1
            if counts[phone] > 1:
                vals_list.remove(vals)
        res = super().create(vals_list)
        return res