import base64
from io import BytesIO

import qrcode

from odoo import fields, models, api, _


def convert_sdt(sdt):
    if sdt:
        sdt_numeric = ''.join(c for c in sdt if c.isdigit())
        if len(sdt_numeric) == 9:
            sdt_numeric = '0' + sdt_numeric
        if len(sdt_numeric) == 10:
            formatted_sdt = "+84" + sdt_numeric[1:]
            return formatted_sdt
        else:
            return sdt
    else:
        return False


class LoyaltyCustomer(models.Model):
    _name = 'loyalty.customer'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Name')
    code = fields.Char('Code')
    barcode = fields.Char('Barcode')
    phone = fields.Char('Phone')
    display_phone = fields.Char('Phone', compute='_hide_phone_customer')
    order_next_rank = fields.Char('Total order next rank', compute='_calculate_total_next_rank')
    money_next_rank = fields.Char('Total money next rank', compute='_calculate_total_next_rank')

    image_1920 = fields.Image("Image", related='partner_id.image_1920', compute_sudo=True)
    qr_code = fields.Binary(string="QR Code", compute='_generate_qr_code')

    type_card_id = fields.Many2one('loyalty.type', string='Type card')
    rank_id = fields.Many2one('loyalty.rank', string='Rank')
    next_rank_id = fields.Many2one('loyalty.rank', string='Next rank', compute='calculate_next_rank')
    partner_id = fields.Many2one('res.partner', string='Partner')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')

    score = fields.Integer('Score', tracking=True)
    total_order = fields.Integer('Total order')

    expiration_date_score = fields.Date('Expiration date score')
    activation_date = fields.Date('Activation date')
    last_rating_date = fields.Date('Last rating date')

    total_spending = fields.Float('Total spending')
    average_spending = fields.Float('Average spending')
    average_spending_display = fields.Char('Average spending')

    state = fields.Selection([('unactivated', 'unactivated'),
                              ('activated', 'Activated'),
                              ('exclude', 'Exclude')],
                             default='unactivated', string='State')

    def create_log(self, vals):
        if self.env.context.get('log_change_score'):
            self.env['loyalty.log.change.score'].sudo().create(vals)
        elif self.env.context.get('log_change_rank'):
            self.env['loyalty.log.change.rank'].sudo().create(vals)

    @api.depends('code')
    def _generate_qr_code(self):
        for record in self:
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(record.code)
            qr.make(fit=True)

            img = qr.make_image(fill='black', back_color='white')

            buffer = BytesIO()
            img.save(buffer, format='PNG')
            qr_image = base64.b64encode(buffer.getvalue())
            record.qr_code = qr_image

    def _calculate_total_next_rank(self):
        for record in self:
            if record.next_rank_id:
                record.order_next_rank = str(record.total_order) + '/' + str(record.next_rank_id.total_order_uprank)
                record.money_next_rank = str(int(record.total_spending)) + '/' + str(
                    int(record.next_rank_id.accumulated_money))

    @api.depends('total_order', 'total_spending')
    def calculate_next_rank(self):
        for record in self:
            domain = []
            if record.total_spending:
                if not domain:
                    domain = [('accumulated_money', '>', record.total_spending)]
                else:
                    domain = ['|', ('accumulated_money', '>', record.total_spending)] + domain
            if record.total_order:
                if not domain:
                    domain = [('total_order_uprank', '>', record.total_order)]
                else:
                    domain = ['|', ('total_order_uprank', '>', record.total_order)] + domain
            next_rank = self.env['loyalty.rank'].sudo().search(domain + [('sequence', '>', record.rank_id.sequence)],
                                                               limit=1, order='sequence ASC')
            # record.next_rank_id = next_rank.id if next_rank else record.rank_id.id
            record.next_rank_id = next_rank.id if next_rank \
                else self.env['loyalty.rank'].sudo().search([], limit=1, order='sequence ASC').id

    def generate_random_barcode(self):
        print('____')

    def exclude_card(self):
        self.ensure_one()
        view_id = self.env.ref('pontusinc_loyalty.popup_reward_view_form').id
        context = {
            'default_loyalty_id': self.id,
            'change_state_exclude': True,
        }
        return {
            'name': _("Exclude card"),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'views': [(view_id, 'form')],
            'res_model': 'popup.rewards',
            'target': 'new',
            'context': context
        }

    def active_card(self):
        self.ensure_one()
        view_id = self.env.ref('pontusinc_loyalty.popup_reward_view_form').id
        context = {
            'default_loyalty_id': self.id,
            'change_state_activated': True,
        }
        return {
            'name': _("Active card"),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'views': [(view_id, 'form')],
            'res_model': 'popup.rewards',
            'target': 'new',
            'context': context
        }

    @api.depends('phone')
    def _hide_phone_customer(self):
        for record in self:
            if record.phone:
                record.display_phone = record.phone[:4] + '******' + record.phone[-2:]
            else:
                record.display_phone = False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('phone') and not vals.get('partner_id'):
                partner = self.env['res.partner'].search([('phone', 'ilike', convert_sdt(vals.get('phone')))],
                                                         limit=1)
                if not partner:
                    vals['partner_id'] = self.env['res.partner'].sudo().create([{
                        'name': vals['name'],
                        'phone': vals['phone']
                    }]).id
        res = super().create(vals_list)
        return res

    @api.onchange('phone')
    def check_info_partner(self):
        self.ensure_one()
        if self.phone:
            partner = self.env['res.partner'].search([('phone', 'ilike', convert_sdt(self.phone))],
                                                     limit=1)
            if partner:
                if self.name:
                    if self.name == partner.name:
                        self.partner_id = partner.id
                    else:
                        self.partner_id = partner.id
                        self.partner_id.write({
                            'name': self.name,
                        })
                else:
                    self.write({
                        'name': partner.name,
                        'partner_id': partner.id,
                    })

    def action_open_log_change_rank(self):
        self.ensure_one()
        view_id = self.env.ref('pontusinc_loyalty.loyalty_log_change_rank_tree_view').id
        context = {
            'default_member_id': self.id,
        }
        return {
            'name': _("Membership class change history"),
            'type': 'ir.actions.act_window',
            'view_mode': 'list',
            'views': [(view_id, 'list')],
            'res_model': 'loyalty.log.change.rank',
            'domain': [('member_id', '=', self.id)],
            'target': 'self',
            'context': context
        }

    def action_open_log_change_score(self):
        self.ensure_one()
        view_id = self.env.ref('pontusinc_loyalty.loyalty_log_change_score_tree_view').id
        context = {
            'default_member_id': self.id,
        }
        return {
            'name': _("Point accumulation change history"),
            'type': 'ir.actions.act_window',
            'view_mode': 'list',
            'views': [(view_id, 'list')],
            'res_model': 'loyalty.log.change.score',
            'domain': [('member_id', '=', self.id)],
            'target': 'self',
            'context': context
        }

    def action_open_popup_reward(self):
        self.ensure_one()
        view_id = self.env.ref('pontusinc_loyalty.popup_reward_view_form').id
        context = {
            'default_loyalty_id': self.id,
            'default_type': 'reward',
        }
        return {
            'name': _("Give bonus points"),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'views': [(view_id, 'form')],
            'res_model': 'popup.rewards',
            'target': 'new',
            'context': context
        }

    def action_open_popup_discount(self):
        self.ensure_one()
        view_id = self.env.ref('pontusinc_loyalty.popup_reward_view_form').id
        context = {
            'default_loyalty_id': self.id,
            'default_type': 'discount',
        }
        return {
            'name': _("Give away discount code"),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'views': [(view_id, 'form')],
            'res_model': 'popup.rewards',
            'target': 'new',
            'context': context
        }

    def action_open_popup_up_rank(self):
        self.ensure_one()
        view_id = self.env.ref('pontusinc_loyalty.popup_reward_view_form').id
        context = {
            'default_loyalty_id': self.id,
            'default_type': 'rank',
        }
        return {
            'name': _("Up rank"),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'views': [(view_id, 'form')],
            'res_model': 'popup.rewards',
            'target': 'new',
            'context': context
        }
