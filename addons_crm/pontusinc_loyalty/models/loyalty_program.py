from odoo import fields, models, api, _

class LoyaltyProgram(models.Model):
    _inherit = 'loyalty.program'

    start_date = fields.Date('Start date')
    end_date = fields.Date('End date')
    recall_duration = fields.Integer('Recall duration')