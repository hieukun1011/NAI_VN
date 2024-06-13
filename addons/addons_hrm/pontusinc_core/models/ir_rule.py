# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo.osv import expression
from odoo.tools import config
from odoo.tools.safe_eval import safe_eval

from odoo import api, models, tools

_logger = logging.getLogger(__name__)

MODEL_HR = ['arrive.late', 'hr.leave', 'project.task', 'account.analytic.line', 'hr.attendance']

class InheritIrRule(models.Model):
    _inherit = 'ir.rule'

    @api.model
    @tools.conditional(
        'xml' not in config['dev_mode'],
        tools.ormcache('self.env.uid', 'self.env.su', 'model_name', 'mode',
                       'tuple(self._compute_domain_context_values())'),
    )
    def _compute_domain(self, model_name, mode="read"):
        rules = self._get_rules(model_name, mode=mode)
        if not rules:
            return

        # browse user and rules as SUPERUSER_ID to avoid access errors!
        eval_context = self._eval_context()
        user_groups = self.env.user.groups_id
        global_domains = []  # list of domains
        group_domains = []  # list of domains
        for rule in rules.sudo():
            # evaluate the domain for the current user
            dom = safe_eval(rule.domain_force, eval_context) if rule.domain_force else []
            dom = expression.normalize_domain(dom)
            if not rule.groups:
                global_domains.append(dom)
            elif rule.groups & user_groups:
                group_domains.append(dom)
        if model_name in MODEL_HR:
            dom = safe_eval(rule.domain_force, eval_context) if rule.domain_force else []
            dom = expression.normalize_domain(dom)
            stt = 0
            for rec in dom:
                if type(rec) == tuple:
                    domain_child_employee = list(rec)
                    if type(rec[0]) == str and 'user_id' in rec[0]:
                        list_member = self.calculate_subordinate_employee_by_user_id(user_id=rec[2])
                        domain_child_employee[1] = 'in'
                        domain_child_employee[2] = list_member
                        dom[stt] = tuple(domain_child_employee)
                stt += 1
                if not rule.groups:
                    global_domains.append(dom)
                elif rule.groups & user_groups:
                    group_domains.append(dom)
            if not group_domains:
                return expression.AND(global_domains)
            return expression.AND(global_domains + [expression.OR(group_domains)])
        # combine global domains and group domains
        if not group_domains:
            return expression.AND(global_domains)
        return expression.AND(global_domains + [expression.OR(group_domains)])

    def calculate_subordinate_employee_by_user_id(self, user_id):
        list_subordinate = []
        if user_id:
            list_subordinate.append(user_id)
            user = self.env['res.users'].sudo().browse(user_id)
            if user.employee_ids and user.employee_ids[0].department_id:
                department = user.employee_ids[0].department_id
                if ((department.manager_id == user.employee_ids[0] or department.deputy_id == user.employee_ids[0])
                        and (department.subordinate_ids and
                             department.subordinate_ids.member_ids and
                             department.subordinate_ids.member_ids.user_id)):
                    list_subordinate += department.subordinate_ids.member_ids.user_id.ids
        return list_subordinate
