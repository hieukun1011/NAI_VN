import json

import requests
from odoo.exceptions import ValidationError, UserError

from odoo import fields, models, api, _
from ...util import convert_address, api_category_vnpost


class ShippingSaleOrder(models.Model):
    _inherit = 'sale.order'

    waybill_id = fields.Many2one('shipping.waybill', string='Waybill')
    platform_id = fields.Many2one('shipping.platform', string='Shipping platform')
    date_inventory = fields.Date('Date of inventory')
    payment_methods = fields.Selection([('cod', 'COD'),
                                        ('online', 'Online'),
                                        ('debit', 'Debit')], default='cod', required=True)
    shipping_fee = fields.Float('Shipping fee')
    collection_fee = fields.Float('Collection fee')
    service_fee = fields.Float('Service fee')
    address_sender = fields.Char('Detailed address')
    city_id = fields.Many2one('res.country.state', string='City',
                              domain=lambda self: [('country_id', '=', self.env.ref('base.vn').id)])
    district_id = fields.Many2one('res.country.district', string='District', domain="[('state_id', '=', city_id)]")
    ward_id = fields.Many2one('res.country.ward', string='Commune', domain="[('district_id', '=', district_id)]")
    receiver_address = fields.Char('Receiver address')
    city_receiver_id = fields.Many2one('res.country.state', string='Receiver province',
                                       domain=lambda self: [('country_id', '=', self.env.ref('base.vn').id)])
    district_receiver_id = fields.Many2one('res.country.district', string='Receiver district',
                                           domain="[('state_id', '=', city_receiver_id)]")
    ward_receiver_id = fields.Many2one('res.country.ward', string='Receiver commune',
                                       domain="[('district_id', '=', district_receiver_id)]")
    weight = fields.Float('Weight', compute='calculation_total_specific_weight', store=True)
    width = fields.Float('Width')
    length = fields.Float('Length')
    height = fields.Float('Height')
    shipping_type = fields.Many2one('shipping.type', string='Shipping type')

    @api.depends('order_line', 'order_line.product_template_id')
    def calculation_total_specific_weight(self):
        for record in self:
            if record.order_line:
                weight = 0
                for rec in record.order_line:
                    if rec.product_template_id:
                        weight += rec.product_template_id.weight
                record.weight = weight

    @api.onchange('warehouse_id')
    def onchange_address_sender_by_warehouse(self):
        self.ensure_one()
        if self.warehouse_id and self.warehouse_id.partner_id:
            address_parts = []
            if self.warehouse_id.partner_id.street:
                address_parts = convert_address.clean_address(self.warehouse_id.partner_id.street)
            elif self.warehouse_id.partner_id.street2:
                address_parts = convert_address.clean_address(self.warehouse_id.partner_id.street2)
            if self.warehouse_id.partner_id.city:
                address_parts.append(self.warehouse_id.partner_id.city)
            city = self.env['res.country.state'].sudo()
            district = self.env['res.country.district'].sudo()
            ward = self.env['res.country.ward'].sudo()
            data_address = {
                'address_sender': '',
                'city_id': False,
                'district_id': False,
                'ward_id': False,
            }
            for rec in reversed(address_parts):
                domain = [('name', 'ilike', rec)]
                if city.search(domain):
                    data_address['city_id'] = city.search(domain).id
                elif district.search(domain + [('state_id', '=', data_address.get('city_id'))]):
                    data_address['district_id'] = district.search(
                        domain + [('state_id', '=', data_address.get('city_id'))]).id
                elif ward.search(domain + [('district_id', '=', data_address.get('district_id'))]):
                    data_address['ward_id'] = ward.search(
                        domain + [('district_id', '=', data_address.get('district_id'))]).id
                else:
                    data_address['address_sender'] = rec + ' ' + data_address['address_sender']
            self.write(data_address)

    @api.onchange('partner_id')
    def onchange_address_sender_by_partner_id(self):
        self.ensure_one()
        if self.partner_id:
            address_parts = []
            if self.partner_id.street:
                address_parts = convert_address.clean_address(self.partner_id.street)
            elif self.partner_id.street2:
                address_parts = convert_address.clean_address(self.partner_id.street2)
            if self.partner_id.city:
                address_parts.append(self.partner_id.city)
            city = self.env['res.country.state'].sudo()
            district = self.env['res.country.district'].sudo()
            ward = self.env['res.country.ward'].sudo()
            data_address = {
                'receiver_address': '',
                'city_receiver_id': False,
                'district_receiver_id': False,
                'ward_receiver_id': False,
            }
            for rec in reversed(address_parts):
                domain = [('name', 'ilike', rec)]
                if city.search(domain):
                    data_address['city_receiver_id'] = city.search(domain).id
                elif district.search(domain + [('state_id', '=', data_address.get('city_receiver_id'))]):
                    data_address['district_receiver_id'] = district.search(
                        domain + [('state_id', '=', data_address.get('city_receiver_id'))]).id
                elif ward.search(domain + [('district_id', '=', data_address.get('district_receiver_id'))]):
                    data_address['ward_receiver_id'] = ward.search(
                        domain + [('district_id', '=', data_address.get('district_receiver_id'))]).id
                else:
                    data_address['receiver_address'] = rec + ' ' + data_address['receiver_address']
            self.write(data_address)

    def call_api_calculation_temporary_shipping_fee(self):
        url = api_category_vnpost.URL_API_VNPOST + api_category_vnpost.shipping_fee
        headers = {
            'token': self.env.user.token_vnpost,
            'Content-Type': 'application/json',
        }
        template = {
            "scope": 1,
            "customerCode": self.env['shipping.platform.user'].sudo().search([('user_id', '=', self.env.user.id),
                                                                              ('platform_id', '=', self.env.ref(
                                                                                  'pontusinc_shipping.shipping_platform_vnpost').id)],
                                                                             limit=1, order='id desc').customer_code,
            "data": {
                "senderProvinceName": self.city_id.name,
                "senderDistrictName": self.district_id.name,
                "senderCommuneName": self.ward_id.name,
                "receiverProvinceName": self.city_receiver_id.name,
                "receiverDistrictName": self.district_receiver_id.name,
                "receiverCommuneName": self.ward_receiver_id.name,
                "receiverNational": "VN",
                "receiverCity": None,
                "orgCodeAccept": None,
                "weight": self.weight * 1000 if self.weight else 0,
                "serviceCode": self.shipping_type.code,
                "addonService": [],
                "additionRequest": [],
                "vehicle": "BO"
            }
        }
        if self.collection_fee:
            service_cod = self.env['shipping.category.service'].sudo().search(
                [('shipping_type_id.code', '=', self.shipping_type.code), ('name', 'ilike', 'COD')], limit=1)
            if service_cod:
                service_properties = self.env['shipping.service.properties'].sudo().search(
                    [('service_id.code', '=', service_cod.code), ('name', 'ilike', 'COD')])
                if service_properties:
                    template['data']['addonService'] = [{
                        'code': service_cod.code,
                        'propValue': service_properties.code + ':' + str(int(self.collection_fee))

                    }]
                else:
                    raise ValidationError(_("COD service properties does not exist!!!"))
            else:
                raise ValidationError(_("COD service does not exist!!!"))
        session = requests.Session()
        response = session.post(url, data=json.dumps(template), headers=headers)
        data = response.json()  # Dữ liệu trả về từ API
        if response.status_code == 200:
            return data
        else:
            raise ValidationError(_(data.get('message')))

    @api.onchange('platform_id', 'payment_methods', 'shipping_type', 'collection_fee')
    def calculation_temporary_shipping_fee(self):
        if self.platform_id and not self.env.user.token_vnpost:
            raise UserError(_('The account has not been connected to the shipping unit.'))
        if self.payment_methods:
            if self.payment_methods == 'cod':
                self.collection_fee = self.amount_total
            if self.platform_id and self.shipping_type:
                shipping_fee = self.call_api_calculation_temporary_shipping_fee()
                if shipping_fee:
                    self.shipping_fee = shipping_fee[0].get('mainFee') if shipping_fee[0].get('mainFee') else 0
                    self.service_fee = shipping_fee[0].get('vasfee') if shipping_fee[0].get('vasfee') else 0

    def action_confirm(self):
        res = super(ShippingSaleOrder, self).action_confirm()
        for record in self:
            if record.platform_id:
                if record.waybill_id:
                    record.waybill_id.state = 'draft'
                else:
                    data = {
                        'name': record.name,
                        'partner_id': record.partner_id.id,
                        'warehouse_id': record.warehouse_id.id,
                        'weight': record.weight,
                        'shipping_platform_id': record.platform_id.id,
                        'shipping_type': record.shipping_type.id,
                        'receiver_address': record.receiver_address,
                        'city_receiver_id': record.city_receiver_id.id,
                        'district_receiver_id': record.district_receiver_id.id,
                        'ward_receiver_id': record.ward_receiver_id.id,
                        'address_sender': record.address_sender,
                        'city_id': record.city_id.id,
                        'district_id': record.district_id.id,
                        'ward_id': record.ward_id.id,
                        'phone_receiver': record.partner_id.phone if record.partner_id.phone else record.partner_id.mobile,
                        'name_receiver': record.partner_id.name,
                        'sale_order_id': record.id,
                    }
                    if record.collection_fee:
                        data['collection_fee'] = record.collection_fee
                    shipping = self.env['shipping.waybill'].sudo().create(data)
                    record.waybill_id = shipping.id
                    shipping.action_post_order_draft_vnpost()
                    if record.picking_ids:
                        if len(record.picking_ids) == 1:
                            record.picking_ids.waybill_id = shipping.id
                        else:
                            for rec in record.picking_ids:
                                if rec.origin == record.name and rec.state != 'cancel':
                                    record.picking_ids.waybill_id = shipping.id
                                    break
        return res

    def action_cancel(self):
        res = super(ShippingSaleOrder, self).action_cancel()
        for record in self:
            if record.waybill_id and self.env.user.token_vnpost:
                record.waybill_id.action_cancel_waybill()
        return res
