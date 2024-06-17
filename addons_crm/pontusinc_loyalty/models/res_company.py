from odoo import fields, models, api, _


class ResCompany(models.Model):
    _inherit = 'res.company'

    auto_active = fields.Selection([('have_orders', 'Generate orders after opening the card'),
                                    ('auto_activate_card', 'Automatically activate the card')],
                                   default='auto_activate_card', required=True)
    have_orders = fields.Boolean('Generate orders after opening the card')
    auto_activate_card = fields.Boolean('Automatically activate the card')
    proviso = fields.Selection([('or', 'OR'),
                                ('and', 'AND')],
                               default='and', string='Proviso')
    minimum_quantity = fields.Integer('Minimum quantity')
    type_minimum_quantity = fields.Selection([('product', 'Product'),
                                              ('order', 'Order')], string='Proviso')
    minimum_spending = fields.Float('Minimum spending')
    score_deadline = fields.Float('Score deadline')
    option_score_deadline = fields.Selection(
        [('last_point_accumulation', 'Calculated from the last point accumulation'),
         ('each_point_accumulation',
          'calculated separately for each point accumulation')], string='Option score deadline')
