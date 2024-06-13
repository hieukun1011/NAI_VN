from odoo import fields, models, api, _

class SpendingDiary(models.Model):
    _name = 'spending.diary'

    code = fields.Char('Code')
    name = fields.Char('Type spending')
    price = fields.Float('Price')
    start_date = fields.Date('Start date')
    end_date = fields.Date('End date')
    partner_id = fields.Many2one('res.partner', string='Partner')
    presenter_id = fields.Many2one(related='partner_id.presenter_id')
    note = fields.Text('Note')

