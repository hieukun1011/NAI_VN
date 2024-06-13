from odoo import fields, models, api


class TagProfiling(models.Model):
    _name = 'tag.profiling'
    _description = 'Tag Profiling'

    name = fields.Char('Name')
