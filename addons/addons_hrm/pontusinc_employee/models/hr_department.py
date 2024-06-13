from odoo import fields, models, api


class HrDepartment(models.Model):
    _inherit = 'hr.department'

    subordinate_ids = fields.One2many('hr.department', string='Subordinates', compute='_compute_subordinates',
                                      help="Direct and indirect subordinates",
                                      compute_sudo=True)

    def _get_subordinates(self, parents=None):
        """
        Helper function to compute subordinates_ids.
        Get all subordinates (direct and indirect) of an employee.
        An employee can be a manager of his own manager (recursive hierarchy; e.g. the CEO is manager of everyone but is also
        member of the RD department, managed by the CTO itself managed by the CEO).
        In that case, the manager in not counted as a subordinate if it's in the 'parents' set.
        """
        if not parents:
            parents = self.env[self._name]

        indirect_subordinates = self.env[self._name]
        parents |= self
        direct_subordinates = self.child_ids - parents
        child_subordinates = direct_subordinates._get_subordinates(
            parents=parents) if direct_subordinates else self.browse()
        indirect_subordinates |= child_subordinates
        return indirect_subordinates | direct_subordinates

    @api.depends('child_ids')
    def _compute_subordinates(self):
        for record in self:
            record.subordinate_ids = record._get_subordinates()
