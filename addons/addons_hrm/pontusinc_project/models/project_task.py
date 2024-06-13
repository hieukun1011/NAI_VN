import pymssql
from odoo.exceptions import UserError

from odoo import fields, models, api, _
from ..util import sync_asana


class ProjectTask(models.Model):
    _inherit = 'project.task'

    point = fields.Float('Point', tracking=True)
    employee_point = fields.Float('Employee point', tracking=True)
    point_done = fields.Float('Point done', compute='_calculate_point_done', store=True)
    asana_id = fields.Char('Asana id')
    is_confirm_point = fields.Boolean('Manager confirm point', default=False)
    no_project = fields.Boolean('No project', default=False)
    show_button = fields.Boolean('Show button', compute='_invisible_button_confirm_point')
    state_ids = fields.Many2many('project.task.type', compute='get_state_user')
    log_ids = fields.One2many('project.task.log', 'task_id', string='Log')
    base_url = fields.Char('URL', compute='render_url_link', store=True)
    type_task = fields.Selection([('feature', 'Feature'),
                                  ('fix', 'Fix'),
                                  ('research', 'Research'),
                                  ('test', 'Test'),
                                  ('refactor', 'Refactor'),
                                  ('optimize', 'Optimize'),
                                  ('docs', 'Docs'),
                                  ('task', 'Task'),
                                  ('other', 'Other')],
                                 default='task', string='Type task')
    backlog_id = fields.Many2one('project.backlog', string='Backlog', tracking=True,
                                 domain="[('project_id', '=', project_id)]")
    department_ids = fields.Many2many('hr.department', compute='_get_department_user', store=True)

    @api.depends('user_ids')
    def _get_department_user(self):
        for record in self:
            if record.user_ids:
                record.department_ids = record.user_ids.department_id
            else:
                record.department_ids = False


    @api.onchange('backlog_id')
    def onchange_milestone(self):
        self.ensure_one()
        if self.backlog_id and not self.milestone_id:
            self.milestone_id = self.backlog_id.milestone_id

    def render_url_link(self):
        url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for record in self:
            if record.name and not record.base_url:
                record.base_url = url + '/web#id=%d&view_type=form&model=%s&action=%d' % (
                    record.id, record._name, self.env.ref('project.action_view_all_task').id)

    @api.depends('project_id')
    def get_state_user(self):
        for record in self:
            if record.project_id:
                record.state_ids = record.project_id.type_ids
            else:
                record.state_ids = False

    @api.depends('is_confirm_point', 'point', 'employee_point', 'stage_id')
    def _calculate_point_done(self):
        for record in self:
            if record.point and not record.is_confirm_point:
                record.point_done = record.point
            else:
                record.point_done = record.employee_point

    @api.depends('parent_id', 'display_project_id', 'no_project')
    def _compute_project_id(self):
        # Avoid recomputing kanban_state
        self.env.remove_to_compute(self._fields['kanban_state'], self)
        for task in self:
            if task.parent_id and not task.no_project:
                task.project_id = task.display_project_id or task.parent_id.project_id
            else:
                task.project_id = self.env.ref('pontusinc_project.project_internal')

    # @api.onchange('no_project')
    # def onchange_project_internal(self):
    #     if self.no_project:
    #         self.project_id = self.env.ref('pontusinc_project.project_internal')
    #     else:
    #         self.project_id = False

    @api.depends('point', 'employee_point')
    def _invisible_button_confirm_point(self):
        for record in self:
            if record.point == record.employee_point and self.project_id.user_id == self.env.user:
                record.show_button = True
            else:
                record.show_button = False

    def confirm_point(self):
        self.is_confirm_point = True

    def return_confirm_point(self):
        self.is_confirm_point = False

    # @api.constrains('stage_id')
    # def save_history_change_state_task(self):
    #     for record in self:
    #         if record.stage_id.id == self.env.ref(
    #                 'pontusinc_project.project_task_type_done').id and self.env.uid not in (
    #                 record.project_id.user_id.ids + record.project_id.project_owner_ids.ids):
    #             raise UserError(
    #                 _("You do not have the right to change the task status to done, please contact the project "
    #                   "manager to perform the above task."))
    #

    @api.model
    def default_get(self, default_fields):
        vals = super(ProjectTask, self).default_get(default_fields)
        vals['display_project_id'] = vals.get('project_id', self.env.context.get('default_project_id'))
        return vals

    def write(self, vals):
        if vals.get('stage_id'):
            if vals.get('stage_id') == self.env.ref('pontusinc_project.project_task_type_done').id:
                if self.env.uid not in (self.project_id.user_id.ids + self.project_id.project_owner_ids.ids):
                    raise UserError(
                        _("You do not have the right to change the task status to done, please contact the project "
                          "manager to perform the above task."))
                if self.stage_id.id != self.env.ref('pontusinc_project.project_task_type_testing').id:
                    raise UserError(_("Please change the status of the task to testing before done!"))
            self.env['project.task.log'].create({
                'task_id': self.id,
                'stage_id': vals.get('stage_id')
            })
        res = super(ProjectTask, self).write(vals)
        return res

    def action_open_log(self):
        view_id = self.env.ref('pontusinc_project.history_change_state_task_view_tree').id
        return {
            'name': _("Log change state"),
            'type': 'ir.actions.act_window',
            'view_mode': 'tree',
            'views': [(view_id, 'tree')],
            'res_model': 'project.task.log',
            'target': 'new',
            'domain': [('id', 'in', self.log_ids.ids)],

        }

    # def write(self, vals):
    #     if vals.get('stage_id') and self.timesheet_ids:
    #         total_point = 0
    #         for sheet in self.timesheet_ids:
    #             total_point += sheet.point
    #         if vals.get('stage_id') == self.env.ref('pontusinc_project.project_task_type_testing').id and total_point != self.employee_point:
    #             raise ValidationError(
    #                 _('The total point in the daily report is not equal to the total point of the task'))
    # if vals.get('stage_id') in [self.env.ref('pontusinc_project.project_task_type_testing').id,
    #                             self.env.ref('pontusinc_project.project_task_type_done').id] and self.timesheet_ids:
    #     total_point = 0
    #     for sheet in self.timesheet_ids:
    #         total_point += sheet.point
    #     point = self.employee_point if self.employee_point and (
    #             self.is_confirm_point or vals.get('stage_id') == self.env.ref(
    #         'pontusinc_project.project_task_type_testing').id) else self.point
    #     if point != total_point:
    #         raise ValidationError(
    #             _('The total point in the daily report is not equal to the total point of the task'))
    # res = super(ProjectTask, self).write(vals)
    # return res

    def sync_data_project_task_asana(self):
        # conn_str = sync_asana.conn_str
        conn = pymssql.connect(sync_asana.server, sync_asana.user, sync_asana.password, sync_asana.database)
        cursor = conn.cursor()
        str_lastcall_child = ''
        str_lastcall_parent = ''
        if self.env.ref('pontusinc_project.ir_cron_sync_project_task').lastcall:
            str_lastcall_child = f" WHERE child.created_at >= '{self.env.ref('pontusinc_project.ir_cron_sync_project_task').lastcall}'"
            str_lastcall_parent = f" AND created_at >= '{self.env.ref('pontusinc_project.ir_cron_sync_project_task').lastcall}'"
        cursor.execute(f'''
                    WITH RecursiveCTE AS (
                        SELECT
                            gid,
                            name,
                            assignee_gid,
                            parent_task_gid,
                            created_at,
                            1 AS level_task
                        FROM
                            AsanaTasks
                        WHERE
                            parent_task_gid IS NULL {str_lastcall_parent}

                        UNION ALL

                        SELECT
                            child.gid,
                            child.name,
                            child.assignee_gid,
                            child.parent_task_gid,
                            child.created_at,
                            parent.level_task + 1
                        FROM
                            AsanaTasks child
                        JOIN
                            RecursiveCTE parent ON child.parent_task_gid = parent.gid
                        {str_lastcall_child}
                    )
                    SELECT
                        rc.gid,
                        rc.name,
                        rc.parent_task_gid,
                        au.email,
                        atp.ProjectId,
                        s.gid as s_gid,
                        s.name as s_name
                    FROM
                        RecursiveCTE rc
                    OUTER APPLY  (SELECT TOP 1 * FROM  AsanaTaskSectionAdd WHERE  rc.gid= TaskId ORDER BY  [DateTime] DESC ) as sa
                    LEFT JOIN AsanaSections s  ON sa.SectionId =s.gid
                    LEFT JOIN AsanaUsers au on au.gid = rc.assignee_gid
                    JOIN AsanaTaskProject atp on atp.TaskId = rc.gid
                    ORDER BY
                    rc.level_task, rc.gid;
                ''')
        rows = cursor.fetchall()
        for row in rows:
            task = self.sudo().search([('asana_id', '=', row[0])])
            if not task:
                vals = {
                    'asana_id': row[0],
                    'name': row[1],
                }
                if row[2]:
                    parent_task = self.sudo().search([('asana_id', '=', row[2])])
                    if parent_task:
                        vals['parent_id'] = parent_task.id
                if row[3]:
                    user = self.env['res.users'].search(['|', ('email', '=', row[3]), ('login', '=', row[3])])
                    vals['user_ids'] = [(6, 0, user.ids)] if user else False
                if row[4]:
                    project = self.env['project.project'].search([('asana_gid', '=', row[4])])
                    if project:
                        vals['project_id'] = project.id
                if row[6]:
                    if row[6] == 'QA':
                        state = self.env.ref('pontusinc_project.project_task_type_testing')
                    elif row[6] in ['New Request', 'New Requests']:
                        state = self.env.ref('pontusinc_project.project_task_type_todo')
                        if state.asana_gid:
                            state.asana_gid += ',' + row[5]
                        else:
                            state.asana_gid = row[5]
                    elif row[6] == 'Doing':
                        state = self.env.ref('pontusinc_project.project_task_type_in_progress')
                        if state.asana_gid:
                            state.asana_gid += ',' + row[5]
                        else:
                            state.asana_gid = row[5]
                    elif row[6] == 'Done':
                        state = self.env.ref('pontusinc_project.project_task_type_done')
                        if state.asana_gid:
                            state.asana_gid += ',' + row[5]
                        else:
                            state.asana_gid = row[5]
                    else:
                        state = self.env.ref('pontusinc_project.project_task_type_backlog')
                        if state.asana_gid:
                            state.asana_gid += ',' + row[5]
                        else:
                            state.asana_gid = row[5]
                    vals['stage_id'] = state.id
                self.with_context(mail_create_nosubscribe=False).sudo().create(vals)
            # else:
            #     if row[5]:
            #         state_task = self.env['project.task.type'].search([('asana_gid', 'ilike', row[5])])
            #         if state_task and state_task.id != task.stage_id.id:
            #             task.stage_id = state_task.id
        # Close the cursor and connection
        cursor.close()
        conn.close()


class Project(models.Model):
    _inherit = 'project.project'

    asana_gid = fields.Char('Asana id')

    def sync_data_project_asana(self):
        conn = pymssql.connect(sync_asana.server, sync_asana.user, sync_asana.password, sync_asana.database)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM AsanaProjects')
        rows = cursor.fetchall()
        vals = []
        for row in rows:
            project = self.sudo().search(['|', ('name', '=', row[1]), ('asana_gid', '=', row[0])])
            if not project:
                vals.append({
                    'asana_gid': row[0],
                    'name': row[1]
                })
        if vals:
            self.create(vals)
        # Close the cursor and connection
        cursor.close()
        conn.close()
