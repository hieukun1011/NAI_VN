# -*- coding: utf-8 -*-
#############################################################################
from odoo import models, fields, api
from odoo.osv import expression


class DashboardMenu(models.Model):
    _name = "dashboard.menu"
    _description = "Dashboard Menu"
    _rec_name = "name"

    name = fields.Char(string="Name")
    menu_id = fields.Many2one('ir.ui.menu', string="Menu",
                              default=lambda self: self.env.ref('odoo_dynamic_dashboard.menu_dashboard').id)
    group_ids = fields.Many2many('res.groups', string='Groups',
                                 related='menu_id.groups_id',
                                 help="User need to be at least in one of these groups to see the menu")
    client_action = fields.Many2one('ir.actions.client')
    embed_code = fields.Text('Embed code')
    sequence = fields.Integer('Sequence')
    view_id = fields.Many2one('ir.ui.view', string='View')
    url_iframe = fields.Char('URL')

    def read_embed_code(self, action_id):
        menu = self.search([('client_action', '=', int(action_id))])
        if menu:
            return menu.url_iframe

    @api.model
    def create(self, vals):
        """This code is to create menu"""
        values = {
            'name': vals['name'],
            'tag': 'owl.dynamic_dashboard',
        }
        action_id = self.env['ir.actions.client'].create(values)
        vals['client_action'] = action_id.id
        menu_id = self.env['ir.ui.menu'].create({
            'name': vals['name'],
            'sequence': vals.get('sequence') or 0,
            'action': 'ir.actions.client,%d' % (action_id.id,)
        })
        if vals.get('embed_code'):
            vals_list = []
            ui_view = self.env['ir.ui.view'].sudo().create({
                    'name': vals['name'],
                    'type': 'qweb',
                    'key': 'iframe_social.' + vals['name'].lower().replace(' ', '_'),
                    'arch': f'''
                        <t t-name="website.{vals['name'].lower().replace(' ', '_')}">
                            <div class="s_embed_code_embedded container o_not_editable">
                                {vals.get('embed_code')}
                            </div>
                        </t>
                    '''
                })
            vals_list.append({
                'name': vals['name'],
                'url': '/' + vals['name'].lower().replace(' ', '_'),
                'is_published': False,
                'view_id': ui_view.id
            })
            view_id = self.env['website.page'].sudo().create(vals_list)
            vals['url_iframe'] = view_id.url
            vals['view_id'] = ui_view.id
        res = super(DashboardMenu, self).create(vals)
        return res

    def write(self, vals):
        if vals.get('embed_code'):
            if self.view_id and self.view_id.page_ids:
                vals['url'] = self.view_id.page_ids[0].url
            else:
                vals_list = []
                vals_list.append({
                    'name': self.name,
                    'url': '/' + self.name.lower().replace(' ', '_'),
                    'is_published': False,
                    'view_id': self.env['ir.ui.view'].sudo().create({
                        'name': self.name,
                        'type': 'qweb',
                        'key': 'iframe_social.' + self.name.lower().replace(' ', '_'),
                        'arch': f'''
                                        <t t-name="website.{self.name.lower().replace(' ', '_')}">
                                            <div class="s_embed_code_embedded container o_not_editable">
                                                {vals.get('embed_code')}
                                            </div>
                                        </t>
                                    '''
                    }).id
                })
                view_id = self.env['website.page'].sudo().create(vals_list)
                vals['url_iframe'] = view_id.url
        result = super(DashboardMenu, self).write(vals)
        return result