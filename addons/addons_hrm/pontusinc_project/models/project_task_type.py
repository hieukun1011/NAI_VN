from odoo import fields, models, api

class ProjectTaskType(models.Model):
    _inherit = 'project.task.type'

    def _get_category_project(self):
        return [('category_id', '=', self.env.ref('base.module_category_services_project').id)]

    asana_gid = fields.Char('Asana id')
    group_ids = fields.Many2one('res.groups', string='Group', domain=_get_category_project)
