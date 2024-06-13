from odoo import fields, models, api

class ProjectTaskLog(models.Model):
    _name = 'project.task.log'
    _description = 'Save task status change history'
    _rec_name = "task_id"

    task_id = fields.Many2one('project.task', string='Task')
    stage_id = fields.Many2one('project.task.type', string='State')
