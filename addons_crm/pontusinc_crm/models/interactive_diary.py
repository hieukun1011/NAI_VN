from odoo import fields, models, api, _

class InteractiveDiary(models.Model):
    _name = 'interactive.diary'
    _rec_name = "action_interactive"

    code = fields.Char('Code')
    name = fields.Char('Title')
    content = fields.Char('Content')
    user_id = fields.Many2one('res.users', string='User')
    action_interactive = fields.Char('Action')
    note = fields.Text('Note')
    partner_id = fields.Many2one('res.partner', string='Partner')
    last_interaction = fields.Datetime('Last interaction')
    count_interactive = fields.Integer('Count interactive')
    interaction_results = fields.Char('Interaction results')
    passive = fields.Boolean('Is passive')
    source = fields.Char('Source')
