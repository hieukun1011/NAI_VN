import json

import requests
from odoo.exceptions import UserError, ValidationError

from odoo import fields, models, api, _
from ..util import convert_address, api_category_vnpost
from ...history_contact.util import log_ulti


class ShippingWaybill(models.Model):
    _name = 'shipping.waybill'
    _order = 'id desc'
    _description = 'Shipping waybill management'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    def _default_warehouse_id(self):
        return self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1).id

    state = fields.Selection(
        [('draft', 'Draft'), ('pending_pickup', 'Pending pickup'), ('in_transit', 'In transit'),
         ('delivered', 'Delivered'), ('pending_redeliver', 'Pending redeliver'),
         ('delivery_canceled_awaiting_pickup', 'Delivery canceled - awaiting pickup'),
         ('delivery_canceled_picked_up', 'Delivery canceled - picked up'), ('cancel', 'Cancel')],
        'State', required=True, default='draft', tracking=True)
    name = fields.Char('Code')
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    packaging_date = fields.Date('Packaging date')
    receiver_id = fields.Many2one('res.partner', string='Receiver')
    phone_receiver = fields.Char('Phone receiver')
    name_receiver = fields.Char('Name receiver')
    shipping_platform_id = fields.Many2one('shipping.platform', string='Shipping platform')
    external_platform_id = fields.Many2one('shipping.platform', string='Shipping platform')
    state_id = fields.Many2one('shipping.state', string='State', tracking=True)
    shipping_fee = fields.Monetary('Shipping fee', currency_field='currency_id')
    collection_fee = fields.Monetary('Collection fee', currency_field='currency_id')
    sale_order_id = fields.Many2one('sale.order', string='Sale order')
    partner_id = fields.Many2one('res.partner', string='Partner')
    user_id = fields.Many2one('res.users', string='User')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    phone_company = fields.Char('Phone stock', default=lambda self: self.env.company.phone)
    type_shipping = fields.Selection(
        [('via_partners', 'Via partners'), ('self_shipment', 'Self-shipment'),
         ('external_shipping', 'External shipping'), ('customer_pickup', 'Customer pickup')],
        'Type shipping', required=True, default='via_partners')
    line_ids = fields.One2many('sale.order.line', 'shipping_id', string='Line shipping',
                               related='sale_order_id.order_line')
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
    fee_payer = fields.Selection([('user', 'User'), ('partner', 'Partner')],
                                 'Fee payer', required=True, default='partner')
    pickup_appointment_date = fields.Date('Pick-up appointment date')
    delivery_appointment_date = fields.Date('Delivery appointment date')
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', default=_default_warehouse_id)
    shipping_type = fields.Many2one('shipping.type', string='Shipping type')
    code_shipping = fields.Char('Code shipping')
    is_broken = fields.Boolean('isBroken')
    weight = fields.Float('Weight', compute='calculate_weight_by_product', store=True)
    item_code = fields.Char('itemCode')
    sale_order_code = fields.Char('saleOrderCode')
    sender_code = fields.Char('senderCode')
    stock_picking_id = fields.Many2one('stock.picking', string="Stock picking")
    case_id = fields.Char('CaseId')

    _sql_constraints = [('unique_code', 'unique(code)', 'Code shipping already exists!!!')]

    @api.onchange('phone_receiver', 'name_receiver')
    def check_info_partner(self):
        self.ensure_one()
        if self.phone_receiver:
            partner = self.env['res.partner'].search([('phone', 'ilike', log_ulti.convert_sdt(self.phone_receiver))],
                                                     limit=1)
            if partner:
                self.write({
                    'name_receiver': partner.name,
                    'partner_id': partner.id,
                })

    @api.onchange('city_receiver_id', 'district_receiver_id', 'ward_receiver_id')
    def check_undeliverable_area(self):
        self.ensure_one()
        if self.city_receiver_id or self.district_receiver_id or self.ward_receiver_id:
            if self.city_receiver_id and self.district_receiver_id.state_id != self.city_receiver_id:
                self.district_receiver_id = False
                self.ward_receiver_id = False
            elif self.district_receiver_id and self.ward_receiver_id.district_id != self.district_receiver_id:
                self.ward_receiver_id = False
            undeliverable_area = self.env['undeliverable.area'].sudo().search([('company_id', '=', self.company_id.id)])
            for area in undeliverable_area:
                if self.city_receiver_id == area.city_id and not area.district_id:
                    raise UserError(_("%s area does not support shipping" % self.city_receiver_id.name))
                elif self.district_receiver_id == area.district_id and not area.ward_id:
                    raise UserError(_("%s area does not support shipping" % self.district_receiver_id.name))
                elif self.ward_receiver_id == area.ward_id and area.ward_id:
                    raise UserError(_("%s area does not support shipping" % self.ward_receiver_id.name))

    @api.depends('line_ids', 'line_ids.product_id')
    def calculate_weight_by_product(self):
        for record in self:
            weight = 0
            if record.line_ids:
                for rec in record.line_ids:
                    weight += rec.product_id.weight
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

    def action_post_order_draft_vnpost(self):
        url = api_category_vnpost.URL_API_VNPOST + api_category_vnpost.post_order
        headers = {
            'token': self.env.user.token_vnpost,
            'Content-Type': 'application/json',
        }
        template = {
            "orderCreationStatus": 0,
            "type": "GUI",
            "informationOrder": {
                "senderMail": None,
                "additionRequest": [],
                "orgCodeCollect": None,
                "orgCodeAccept": None,
                "vehicle": "BO",
                "sendType": "1",
                "deliveryTime": "N",
                "deliveryRequire": "1",
                "deliveryInstruction": None,
                "receiverCommuneCode": None,
                "senderDistrictCode": None,
                "senderCommuneCode": None,
                "receiverDistrictCode": None,
                "receiverEmail": None,
            }
        }
        value = self.action_create_order_vnpost()
        template['informationOrder'].update(value)
        session = requests.Session()
        response = session.post(url, data=json.dumps(template), headers=headers)
        data = response.json()  # Dữ liệu trả về từ API
        if response.status_code == 200:
            vals = {}
            if data.get('totalFee'):
                vals['shipping_fee'] = data.get('totalFee')
            if data.get('status'):
                vals['state_id'] = self.env.ref('pontusinc_shipping.shipping_state_' + str(data.get('status')))
            if data.get('originalID'):
                vals['code_shipping'] = data.get('originalID')
            if vals:
                self.write(vals)
        else:
            raise ValidationError(_(data.get('message')))

    def action_post_order_pending_vnpost(self):
        url = api_category_vnpost.URL_API_VNPOST + api_category_vnpost.post_order
        headers = {
            'token': self.env.user.token_vnpost,
            'Content-Type': 'application/json',
        }
        template = {
            "orderCreationStatus": 1,
            "type": "GUI",
            "informationOrder": {
                "senderMail": None,
                "additionRequest": [],
                "orgCodeCollect": None,
                "orgCodeAccept": None,
                "vehicle": "BO",
                "sendType": "1",
                "deliveryTime": "N",
                "deliveryRequire": "1",
                "deliveryInstruction": None,
                "receiverCommuneCode": None,
                "senderDistrictCode": None,
                "senderCommuneCode": None,
                "receiverDistrictCode": None,
                "receiverEmail": None,
            }
        }
        value = self.action_create_order_vnpost()
        template['informationOrder'].update(value)
        session = requests.Session()
        response = session.post(url, data=json.dumps(template), headers=headers)
        data = response.json()  # Dữ liệu trả về từ API
        if response.status_code == 200:
            vals = {
                'state': 'pending_pickup'
            }
            if data.get('totalFee'):
                vals['shipping_fee'] = data.get('totalFee')
            if data.get('status'):
                vals['state_id'] = self.env.ref('pontusinc_shipping.shipping_state_' + str(data.get('status')))
            if data.get('originalID'):
                vals['code_shipping'] = data.get('originalID')
            if vals:
                self.write(vals)
        else:
            raise ValidationError(_(data.get('message')))

    def action_create_order_vnpost(self):
        for record in self:
            value = {
                "senderName": self.env.user.name,
                "addonService": [],
                "senderPhone": record.phone_company,
                "senderAddress": record.address_sender,
                "senderProvinceCode": record.city_id.code_vnpost,
                "senderProvinceName": record.city_id.name,
                "senderDistrictName": record.district_id.name,
                "senderCommuneName": record.ward_id.name,
                "receiverName": record.partner_id.name,
                "receiverAddress": record.receiver_address,
                "receiverProvinceCode": record.city_receiver_id.code_vnpost,
                "receiverProvinceName": record.city_receiver_id.name,
                "receiverDistrictName": record.district_receiver_id.name,
                "receiverCommuneName": record.ward_receiver_id.name,
                "receiverPhone": record.partner_id.phone or record.partner_id.mobile,
                "serviceCode": record.shipping_type.code,
                "saleOrderCode": record.name,
                "contentNote": 'mô tả',
                "weight": "1000",
                "width": None,
                "length": None,
                "height": None,
            }
            if record.fee_payer == 'partner':
                service = self.env['shipping.category.service'].sudo().search(
                    [('shipping_type_id', '=', record.shipping_type.id), ('name', 'ilike', 'Thu hộ phí ship')], limit=1)
                if service:
                    value['addonService'] += [{
                        'code': service.code,
                        'propValue': None
                    }]
                else:
                    raise ValidationError(_("Delivery fee collection service does not exist!!!"))
            if record.collection_fee:
                service_cod = self.env['shipping.category.service'].sudo().search(
                    [('shipping_type_id', '=', record.shipping_type.id), ('name', 'ilike', 'COD')], limit=1)
                if service_cod:
                    service_properties = self.env['shipping.service.properties'].sudo().search(
                        [('service_id', '=', service_cod.id), ('name', 'ilike', 'COD')])
                    if service_properties:
                        value['addonService'] += [{
                            'code': service_cod.code,
                            'propValue': service_properties.code + ':' + str(int(record.collection_fee))

                        }]
                    else:
                        raise ValidationError(_("COD service properties does not exist!!!"))
                else:
                    raise ValidationError(_("COD service does not exist!!!"))
            if record.is_broken:
                value['isBroken'] = 1
            else:
                value['isBroken'] = 0
            return value

    def post_order_by_draft(self):
        url = api_category_vnpost.URL_API_VNPOST + api_category_vnpost.post_order_by_draft
        headers = {
            'token': self.env.user.token_vnpost,
            'Content-Type': 'application/json',
        }
        params = {
            'type': '3',
            'code': self.code_shipping
        }
        session = requests.Session()
        response = session.get(url, params=params, headers=headers)
        data = response.json()
        if response.status_code == 200:
            self.state = 'pending_pickup'
        else:
            raise ValidationError(_(data.get('message')))

    def write(self, vals):
        print(vals)
        return super(ShippingWaybill, self).write(vals)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            print('_____')
            if vals.get('phone_receiver') and vals.get('name_receiver') and not vals.get('partner_id'):
                vals['partner_id'] = self.env['res.partner'].sudo().create({
                    'name': vals.get('name_receiver'),
                    'phone': vals.get('phone_receiver'),
                    'mobile': vals.get('phone_receiver'),
                    'state_id': vals.get('city_receiver_id'),
                }).id
        res = super(ShippingWaybill, self).create(vals_list)
        if res.partner_id and not res.partner_id.street:
            res.partner_id.street = res.receiver_address + ', ' + res.ward_receiver_id.name + ', ' + res.district_receiver_id.name + ', ' + res.ward_receiver_id.name
        return res

    def action_cancel_waybill(self):
        url = api_category_vnpost.URL_API_VNPOST + api_category_vnpost.cancel_waybill
        headers = {
            'token': self.env.user.token_vnpost,
            'Content-Type': 'application/json',
        }
        template = {
            "OriginalId": self.code_shipping,
        }
        session = requests.Session()
        response = session.post(url, data=json.dumps(template), headers=headers)
        data = response.json()  # Dữ liệu trả về từ API
        if response.status_code == 200:
            vals = {
                'case_id': data[0]['caseId'],
                'code_shipping': False,
                'state': 'cancel'
            }
            self.write(vals)
            return True
        else:
            raise ValidationError(_(data.get('message')))

    # def action_write_shipping_waybill_vn_post(self):
    #     url = api_category_vnpost.URL_API_VNPOST + api_category_vnpost.write_order
    #     headers = {
    #         'token': self.env.user.token_vnpost,
    #         'Content-Type': 'application/json',
    #     }
    #     template = {
    #         "OriginalId": self.code_shipping,
    #         "SourceCode": "MYVNP",
    #         "ServiceCode": "ETN011",
    #         "ItemCode": "BK990032289VN",
    #         "AffairType": "02",
    #         "OrderCode": "BK990032289VN",
    #         "FlagConfig": "1",
    #         "Contents": "kem dưỡng da",
    #         "Vehicle": "BO",
    #         "UndeliverGuide": "",
    #         "POPickupCode": "119511",
    #         "PickupDateTime": "",
    #         "CODAmount": 12222,
    #         "Sender": {
    #             "OrgCode": "C000208283",
    #             "ContractNumber": "Hợp đồng số 1",
    #             "ContractType": "",
    #             "CustomerName": "",
    #             "Phone": "094xxxxxxx",
    #             "Fullname": "Phạm Bảo Bích",
    #             "Address": "129 NGUYỄN TRÃI , TT CƠ KHÍ P. Khương Trung Q. Thanh Xuân Hà Nội",
    #             "Province": "10",
    #             "ProvinceName": "",
    #             "District": "1100",
    #             "DistrictName": "",
    #             "Commune": "11006",
    #             "CommuneName": "",
    #             "Postcode": "11006",
    #             "Lon": "",
    #             "Lat": "",
    #             "Vpostcode": ""
    #         },
    #         "Receiver": {
    #             "OrgCode": "",
    #             "ContractNumber": "HD1234567",
    #             "ContractType": "PPA",
    #             "CustomerName": "",
    #             "Phone": "094xxxxxxx",
    #             "Fullname": "Phạm Bảo Bích",
    #             "Address": "129 NGUYỄN TRÃI , TT CƠ KHÍ P. Khương Trung Q. Thanh Xuân Hà Nội",
    #             "Province": "10",
    #             "ProvinceName": "",
    #             "District": "1140",
    #             "DistrictName": "",
    #             "Commune": "11413",
    #             "CommuneName": "",
    #             "Postcode": "11413",
    #             "SortingCode": "114500",
    #             "Lon": "",
    #             "Lat": "",
    #             "Vpostcode": ""
    #         },
    #         "Addons": [
    #             {
    #                 "ServiceCode": "GTG021",
    #                 "Props": [
    #                     {
    #                         "PropCode": "PROP0018",
    #                         "PropValue": "12000"
    #                     },
    #                     {
    #                         "PropCode": "PROP0043",
    #                         "propValue": "15000"
    #                     },
    #                     {
    #                         "PropCode": "PROP0003",
    #                         "PropValue": "16/75 HỒ TÙNG MẬU P. Mai Dịch Q. Cầu Giấy Hà Nội"
    #                     }
    #                 ]
    #             }
    #         ],
    #         "Package": {
    #             "Weight": "2000",
    #             "Length": "",
    #             "Width": "",
    #             "Height": "",
    #             "Volume": "",
    #             "PriceWeight": "2000",
    #             "DimWeight": "",
    #             "IsVolume": false
    #         }
    #     }
