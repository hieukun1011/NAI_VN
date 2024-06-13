from odoo import fields, models

class ResPartner(models.Model):
    _inherit = 'res.partner'

    facebook_id = fields.Char('Facebook ID')
    company_name = fields.Char('Company Name')
    school_name = fields.Char('School Name')
    province = fields.Char('Province')
    hometown = fields.Char('Hometown')
    checkin_location = fields.Char('Checkin location')
