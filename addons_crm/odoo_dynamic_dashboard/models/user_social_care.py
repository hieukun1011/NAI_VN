from odoo import fields, models, api


class UserSocialCare(models.Model):
    _name = 'user.social.care'

    login = fields.Char('login')
    password = fields.Char(copy=False, string='Password',
        help="Keep empty if you don't want the user to be able to connect on the system.")
    user_id = fields.Many2one('res.users', string='User')
