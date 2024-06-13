from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ProjectBacklog(models.Model):
    _name = 'project.backlog'
    _description = 'Project backlog'

    name = fields.Char('Name')
    start_date = fields.Date('Start date')
    end_date = fields.Date('End date')
    milestone_id = fields.Many2one('project.milestone', string='Milestone')
    task_ids = fields.One2many('project.task', 'backlog_id', string='Task')
    project_id = fields.Many2one(related='milestone_id.project_id', string='Project_id')

    @api.constrains('end_date')
    def check_end_date(self):
        for record in self:
            if record.end_date and record.milestone_id and record.milestone_id.deadline and record.milestone_id.deadline < record.end_date:
                raise UserError(_("The backlog end date cannot be greater than the milestone end date."))

class ProjectMilestone(models.Model):
    _inherit = 'project.milestone'

    backlog_ids = fields.One2many('project.backlog', 'milestone_id', string='Backlog')