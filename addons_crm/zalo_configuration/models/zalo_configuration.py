# -*- coding: utf-8 -*-

import json
import base64
import requests

from datetime import datetime, timedelta
from odoo import models, fields, api, tools
from odoo.exceptions import UserError

class ZaloConfiguration(models.Model):
    _name = 'zalo.configuration'
    _description = 'Zalo Configuration'

    name = fields.Char('Name')
    app_id = fields.Char('App ID')
    app_secret = fields.Char('App Secret')
    authorization_url = fields.Text('Authorization URL')
    authorization_code = fields.Text('Authorization Code')
    code_verifier = fields.Text('Code Verifier')
    access_token = fields.Text('Access Token')
    refresh_token = fields.Text('Refresh Token')
    expire_in = fields.Datetime('Expire In')

    def get_authorization_code(self):
        if self.authorization_url:
            return {
                'type': 'ir.actions.act_url',
                'url': self.authorization_url,
                'target': 'new'
            }

    def get_access_token(self):
        if not self:
            self = self.env.ref('zalo_configuration.zalo_configuration')
        self.ensure_one()
        time_now = fields.Datetime.now()

        if not (self.authorization_code and self.app_secret and self.app_id):
            return

        url = 'https://oauth.zaloapp.com/v4/oa/access_token'
        header = {
            'secret_key': self.app_secret,
            'Content-Type': 'application/x-www-form-urlencoded',
        }
        body = {}
        if self.refresh_token and (not self.expire_in or (self.expire_in and time_now > self.expire_in)):
            body = {
                'refresh_token': self.refresh_token,
                'app_id': self.app_id,
                'grant_type': 'refresh_token',
            }
        elif not self.access_token:
            body = {
                'code': self.authorization_code,
                'app_id': self.app_id,
                'grant_type': 'authorization_code',
                'code_verifier': self.code_verifier or '',
            }

        if body:
            resp = requests.post(url=url, headers=header, data=body)
            resp_json = resp.json()
            if resp_json.get('access_token', False):
                self.access_token = resp_json.get('access_token')
            if resp_json.get('refresh_token', False):
                self.refresh_token = resp_json.get('refresh_token')
                self.expire_in = time_now + timedelta(seconds=8500)
        return self.access_token

    def reset_access_token(self):
        if not self:
            self = self.env.ref('zalo_configuration.zalo_configuration')
        self.ensure_one()
        time_now = fields.Datetime.now()

        if not (self.authorization_code and self.app_secret and self.app_id):
            return

        url = 'https://oauth.zaloapp.com/v4/oa/access_token'
        header = {
            'secret_key': self.app_secret,
            'Content-Type': 'application/x-www-form-urlencoded',
        }
        body = {
            'refresh_token': self.refresh_token,
            'app_id': self.app_id,
            'grant_type': 'refresh_token',
        }
        if body:
            resp = requests.post(url=url, headers=header, data=body)
            resp_json = resp.json()
            if resp_json.get('access_token', False):
                self.access_token = resp_json.get('access_token')
            if resp_json.get('refresh_token', False):
                self.refresh_token = resp_json.get('refresh_token')
                self.expire_in = time_now + timedelta(seconds=8500)
        return self.access_token

    
    def get_user_profile(self, user_id, raise_exception=True):
        if not user_id:
            return '', False
        partner_id = self.env['res.partner'].search([('zalo_user_id','=',user_id)], limit=1)
        if not partner_id:
            access_token = self.get_access_token()
            url = 'https://openapi.zalo.me/v2.0/oa/getprofile?data={"user_id":"%s"}' % user_id.replace(' ','')
            header = {
                'access_token': access_token,
                'appsecret_proof': self.env.ref('zalo_configuration.zalo_configuration').generate_appsecret_proof(),
            }
            resp = requests.get(url=url, headers=header)
            resp_json = resp.json()
            if resp_json.get('error', False):
                if raise_exception:
                    raise UserError(resp_json.get('message'))
                else:
                    return ''

            # get avatar
            avatar_url = resp_json['data'].get('avatars',[]) and resp_json['data']['avatars'].get('240','') or resp_json['data'].get('avatar','')
            avatar = ''
            if avatar_url:
                avatar_request = requests.get(avatar_url)
                avatar = avatar_request.content
            # create contact
            partner_id = self.env['res.partner'].create({
                'name': resp_json['data'].get('display_name',user_id),
                'image_1920': base64.b64encode(avatar),
                'zalo_user_id': user_id,
            })
        return partner_id