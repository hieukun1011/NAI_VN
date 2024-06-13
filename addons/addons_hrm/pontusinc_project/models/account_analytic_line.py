from odoo import fields, models, api, _
from datetime import datetime, date, timedelta

from odoo.exceptions import UserError


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    point = fields.Float('Point')

    # @api.model_create_multi
    # def create(self, vals_list):
    #     for vals in vals_list:
    #         if vals.get('date') and not (vals.get('global_leave_id') or vals.get('holiday_id')) and datetime.strptime(str(vals.get('date')), "%Y-%m-%d").date() < date.today():
    #             if datetime.strptime(str(vals.get('date')), "%Y-%m-%d").date() < date.today() - timedelta(days=1):
    #                 raise UserError(_("Reporting date has expired %s" % vals.get('date')))
    #             else:
    #                 if datetime.now().hour > 5:
    #                     raise UserError(_("Reporting date has expired %s" % vals.get('date')))
    #
    #     records = super(AccountAnalyticLine, self).create(vals_list)
    #     return records