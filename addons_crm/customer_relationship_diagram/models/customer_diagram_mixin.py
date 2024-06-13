# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class HrEmployeeBase(models.AbstractModel):
    _inherit = 'res.partner'

    # child_all_count = fields.Integer(
    #     'Indirect Subordinates Count',
    #     compute='_compute_subordinates', recursive=True, store=False,
    #     compute_sudo=True)
    # subordinate_ids = fields.One2many('res.partner', string='Subordinates', compute='_compute_subordinates',
    #                                   help="Direct and indirect subordinates",
    #                                   compute_sudo=True)
    #
    # def _get_subordinates(self, parents=None):
    #     """
    #     Helper function to compute subordinates_ids.
    #     Get all subordinates (direct and indirect) of an employee.
    #     An employee can be a manager of his own manager (recursive hierarchy; e.g. the CEO is manager of everyone but is also
    #     member of the RD department, managed by the CTO itself managed by the CEO).
    #     In that case, the manager in not counted as a subordinate if it's in the 'parents' set.
    #     """
    #     if not parents:
    #         parents = self.env[self._name]
    #
    #     indirect_subordinates = self.env[self._name]
    #     parents |= self
    #     direct_subordinates = self.child_presenter_ids - parents
    #     child_subordinates = direct_subordinates._get_subordinates(parents=parents) if direct_subordinates else self.browse()
    #     indirect_subordinates |= child_subordinates
    #     return indirect_subordinates | direct_subordinates
    #
    #
    # @api.depends('child_presenter_ids', 'child_presenter_ids.child_all_count')
    # def _compute_subordinates(self):
    #     for partner in self:
    #         partner.subordinate_ids = partner._get_subordinates()
    #         partner.child_all_count = len(partner.subordinate_ids)
