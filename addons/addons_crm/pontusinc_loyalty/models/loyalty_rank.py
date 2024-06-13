from odoo import fields, models, api, _


class LoyaltyRank(models.Model):
    _name = 'loyalty.rank'

    name = fields.Char('Name', translate=True)

    sequence = fields.Integer('Sequence')
    count_member = fields.Integer('Count member')
    text_color = fields.Integer(string='Text color')
    background_color = fields.Integer(string='Background color')
    accumulated_money = fields.Float('Accumulated money')
    ewallet_money = fields.Float('E-wallet money')
    total_money = fields.Float('Total money')
    total_order = fields.Integer('Total order')
    total_order_uprank = fields.Integer('Total order')
    total_order_in_month = fields.Float('Month')
    total_money_in_month = fields.Float('Month')
    money_month_maintain = fields.Float('Month')
    order_month_maintain = fields.Float('Month')

    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    loyalty_program_ids = fields.Many2many('loyalty.program')

    proviso = fields.Selection([('or', 'OR'),
                                ('and', 'AND')],
                               default='and', string='Proviso')
    proviso_maintain = fields.Selection([('or', 'OR'),
                                         ('and', 'AND')],
                                        default='and', string='Proviso')

    attachment_ids = fields.Many2many('ir.attachment', string='Attachment')

    def action_open_loyalty_customer(self):
        self.ensure_one()
        view_id = self.env.ref('pontusinc_loyalty.loyalty_customer_tree_view').id
        context = {
            'default_rank_id': self.id,
        }
        return {
            'name': _("Loyalty card"),
            'type': 'ir.actions.act_window',
            'view_mode': 'list',
            'views': [(view_id, 'list'), (False, 'form')],
            'res_model': 'loyalty.customer',
            'target': 'new',
            'domain': [('rank_id', '=', self.id)],
            'context': context
        }
