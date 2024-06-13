from odoo import models, fields, api, _


class ProjectProject(models.Model):
    _inherit = 'project.project'

    is_internal = fields.Boolean('Project internal')
    project_owner_ids = fields.Many2many('res.users', 'user_project_owner_rel', string='Project owner')
    department_ids = fields.Many2many('hr.department', 'project_department_rel', string='Department')
    manager_follower_ids = fields.Many2many('hr.employee', string='Manager follower',
                                            compute='get_recursive_manager_department', store=True)

    def find_parent_departments(self, departments, parent_departments=None):
        if parent_departments is None:
            parent_departments = set()

        for department in departments:
            parent_department = department.parent_id
            if parent_department:
                parent_departments.add(parent_department)
                self.find_parent_departments([parent_department], parent_departments)

        return parent_departments

    @api.depends('department_ids')
    def get_recursive_manager_department(self):
        for record in self:
            if record.department_ids:
                all_parent_departments = set(record.department_ids)
                parent_departments = self.find_parent_departments(record.department_ids)
                all_parent_departments |= parent_departments
                list_po = []
                for parent_department in all_parent_departments:
                    list_po.append(parent_department.manager_id.id)
                    list_po.append(parent_department.deputy_id.id)
                record.write({'manager_follower_ids': [(6, 0, list_po)]})

    def _prepare_variant_values(self, combination):
        variant_dict = super()._prepare_variant_values(combination)
        variant_dict['base_unit_count'] = self.base_unit_count
        return variant_dict

    def action_view_tasks(self):
        action = super().action_view_tasks()
        self_stage_task = self.env['project.task.type'].search([('project_ids', '=', self.id)])
        action['domain'] = f"""[('display_project_id', '=', active_id), ('stage_id', 'in', {self_stage_task.ids})]"""
        return action

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('type_ids'):
                vals['type_ids'] = self.env['project.task.type'].sudo().search([('user_id', '=', False)]).ids
        res = super(ProjectProject, self).create(vals_list)
        return res

    def action_get_list_view_backlog(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("%(name)s's Backlog", name=self.name),
            'domain': [('project_id', '=', self.id)],
            'res_model': 'project.backlog',
            'views': [(self.env.ref('pontusinc_project.project_backlog_view_tree').id, 'tree')],
            'view_mode': 'tree',
            'help': _("""
                <p class="o_view_nocontent_smiling_face">
                    No backlog found. Let's create one!
                </p><p>
                    Track major progress points that must be reached to achieve success.
                </p>
            """),
            'context': {
                'default_project_id': self.id,
                **self.env.context
            }
        }
