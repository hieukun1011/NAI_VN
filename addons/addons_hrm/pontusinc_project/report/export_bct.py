from datetime import date, datetime

from dateutil.relativedelta import relativedelta

from odoo import fields, models, api, _
from odoo.exceptions import UserError

month = [('01', 'January'),
         ('02', 'February'),
         ('03', 'March'),
         ('04', 'April'),
         ('05', 'May'),
         ('06', 'June'),
         ('07', 'July'),
         ('08', 'August'),
         ('09', 'September'),
         ('10', 'October'),
         ('11', 'November'),
         ('12', 'December')]

year = [('2020', '2020'),
        ('2021', '2021'),
        ('2022', '2022'),
        ('2023', '2023'),
        ('2024', '2024'),
        ('2025', '2025'),
        ('2026', '2026'),
        ('2027', '2027'),
        ('2028', '2028'),
        ('2029', '2029'),
        ('2030', '2030')]


class ExportBCTDetail(models.Model):
    _name = 'export.bct.detail'
    _description = 'Export report months detail'

    user_id = fields.Many2one('res.users', string='User')
    point = fields.Float('Point')
    bct_id = fields.Many2one('export.bct')

    def domain_show_detail(self, bct_id):
        if bct_id.month and bct_id.year:
            if bct_id.month == '12':
                str_year = str(int(bct_id.year) + 1) + '-01'
            else:
                str_year = bct_id.year + '-' + str(int(bct_id.month) + 1)
            query = f'''
                SELECT
                    pt.id
                FROM
                    project_task pt
                JOIN project_task_user_rel ptur on ptur.task_id = pt.id
                JOIN res_users ru on ru.id = ptur.user_id 
                LEFT JOIN LATERAL (
                                SELECT create_date 
                                FROM project_task_log 
                                WHERE stage_id = {self.env.ref('pontusinc_project.project_task_type_testing').id} 
                                    AND pt.id = project_task_log.task_id  
                                ORDER BY create_date DESC LIMIT 1) AS QATime ON true
                LEFT JOIN LATERAL (
                                SELECT create_date 
                                FROM project_task_log 
                                WHERE stage_id = {self.env.ref('pontusinc_project.project_task_type_done').id} 
                                    and pt.id = project_task_log.task_id 
                                ORDER BY create_date DESC LIMIT 1) AS DoneTime ON true
                WHERE 
                    ru.id = {self.user_id.id}
                    AND
                        ((QATime.create_date IS NULL 
                            AND DoneTime.create_date BETWEEN '{bct_id.year + '-' + bct_id.month + '-01'}' 
                            AND '{str_year + '-01'}')
                        OR 
                        (QATime.create_date BETWEEN '{bct_id.year + '-' + bct_id.month + '-01'}' 
                            AND '{str_year + '-01'}' AND DoneTime.create_date BETWEEN '{bct_id.year + '-' + bct_id.month + '-01'}'
                            AND '{str_year + '-05'}')
                        OR 
                        (DoneTime.create_date BETWEEN '{bct_id.year + '-' + bct_id.month + '-05'}' 
                            AND '{str_year + '-01'}'))
                GROUP BY pt.id
            '''
            self._cr.execute(query)
            dict_data = self._cr.dictfetchall()
            domain = [item['id'] for item in dict_data]
            return [('id', 'in', domain)]

    def show_detail(self):
        tree_id = self.env.ref('project.view_task_tree2').id
        form_id = self.env.ref('project.view_task_form2').id
        domain = self.domain_show_detail(self.bct_id)
        return {
            'name': _("Project task"),
            'type': 'ir.actions.act_window',
            'view_mode': 'list,form',
            'views': [(tree_id, 'list'), (form_id, 'form')],
            'res_model': 'project.task',
            'domain': domain,
        }


class ExportBCT(models.Model):
    _name = 'export.bct'
    _description = 'Export report months'

    name = fields.Char('Name', compute='_get_name', store=True)
    month = fields.Selection(month, required=True, string='Month')
    year = fields.Selection(year, required=True, string='Month')
    company_ids = fields.Many2many('res.company', 'export_bct_select_company_rel', string='Company',
                                   default=lambda self: self.env.user.company_ids.ids)
    detail_ids = fields.One2many('export.bct.detail', 'bct_id', string='Detail')

    @api.constrains('month', 'year')
    def constrains_month_report(self):
        for record in self:
            if record.month and record.year and len(
                    self.sudo().search([('year', '=', record.year), ('month', '=', record.month)])) > 1:
                raise UserError(_("Report months %s-%s already exist." % (record.month, record.year)))

    @api.depends('month', 'year')
    def _get_name(self):
        for record in self:
            if record.month and record.year:
                record.name = 'Report month ' + record.month + '/' + record.year

    def action_report_months(self):
        if self.month and self.year:
            if self.month == '12':
                str_year = str(int(self.year) + 1) + '-01'
            else:
                str_year = self.year + '-' + str(int(self.month) + 1)
            query = f'''
                SELECT SUM(total.point_done) as total_point_done, total.user_id
                FROM (
                    SELECT
                        pt.id,
                        pt.point_done,
                        ru.id as user_id
                    FROM
                        project_task pt
                    JOIN project_task_user_rel ptur on ptur.task_id = pt.id
                    JOIN res_users ru on ru.id = ptur.user_id 
                    LEFT JOIN LATERAL (
                                    SELECT create_date 
                                    FROM project_task_log 
                                    WHERE stage_id = {self.env.ref('pontusinc_project.project_task_type_testing').id} 
                                        AND pt.id = project_task_log.task_id  
                                    ORDER BY create_date DESC LIMIT 1) AS QATime ON true
                    LEFT JOIN LATERAL (
                                    SELECT create_date 
                                    FROM project_task_log 
                                    WHERE stage_id = {self.env.ref('pontusinc_project.project_task_type_done').id} 
                                        and pt.id = project_task_log.task_id 
                                    ORDER BY create_date DESC LIMIT 1) AS DoneTime ON true
                    WHERE 
                        (QATime.create_date IS NULL 
                            AND DoneTime.create_date BETWEEN '{self.year + '-' + self.month + '-01'}' 
                            AND '{str_year + '-01'}')
                        OR 
                        (QATime.create_date BETWEEN '{self.year + '-' + self.month + '-01'}' 
                            AND '{str_year + '-01'}' AND DoneTime.create_date BETWEEN '{self.year + '-' + self.month + '-01'}'
                             AND '{str_year + '-05'}')
                        OR 
                        (DoneTime.create_date BETWEEN '{self.year + '-' + self.month + '-05'}' 
                            AND '{str_year + '-01'}')
                    GROUP BY pt.id, pt.point_done, ru.id) as total
                GROUP BY total.user_id;
            '''

            self._cr.execute(query)
            dict_data = self._cr.dictfetchall()
            if dict_data:
                self.detail_ids.unlink()
                sql_query = "INSERT INTO export_bct_detail (user_id, point, bct_id) VALUES "
                sql_query += ", ".join(
                    [f"({record['user_id']}, {record['total_point_done']}, {self.id})" for record in dict_data])
                self.env.cr.execute(sql_query)
