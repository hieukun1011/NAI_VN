# -*- coding: utf-8 -*-
import logging

from odoo import http
from odoo.http import request
from ..JwtRequest import jwt_request

_logger = logging.getLogger(__name__)

SENSITIVE_FIELDS = ['password', 'password_crypt', 'new_password', 'create_uid', 'write_uid']


class JwtController(http.Controller):

    @http.route('/api/http/hello', type='http', auth='public', csrf=False, cors='*')
    @jwt_request.middlewares('api_key')
    def hello(self, **kw):
        return jwt_request.response({'message': 'hello!', 'key_info': jwt_request.data.get('key_info')})

    @http.route('/auths/verify-login', type='json', auth='public', csrf=False, cors='*', methods=['POST'], api_key='X-Sogo-Access-Token')
    @jwt_request.middlewares('api_key')
    def login(self):
        try:
            payload = request.get_json_data()
            username = payload.get("username")
            password = payload.get("password")
            if not username or not password:
                return jwt_request.response({"message": "The username or password is incorrect"}, 400)
            result = jwt_request.login(username, password)
            return self._response_auth(result)
        except Exception as e:
            print(e)
            return {
                "status": 500,
                "message": "Server error"
            }

    @http.route('/api/http/me', type='http', auth='public', csrf=False, cors='*')
    @jwt_request.middlewares('jwt')
    def me(self, **kw):
        return jwt_request.response(request.env.user.to_dict())

    @http.route('/api/http/logout', type='http', auth='public', csrf=False, cors='*')
    @jwt_request.middlewares('jwt')
    def logout(self, **kw):
        jwt_request.logout()
        return jwt_request.response()

    # @http.route('/api/http/register', type='http', auth='public', csrf=False, cors='*', methods=['POST'])
    # def register(self, email=None, name=None, password=None, **kw):
    #     """
    #     In previous version, we use auth_signup to register an external (portal) user.
    #     For this demo, we use res.users.create instead, this will create an internal user
    #     """
    #     if not is_valid_email(email):
    #         return jwt_request.response(status=400, data={'message': 'Invalid email address'})
    #     if not name:
    #         return jwt_request.response(status=400, data={'message': 'Name cannot be empty'})
    #     if not password:
    #         return jwt_request.response(status=400, data={'message': 'Password cannot be empty'})
    #
    #     # sign up
    #     try:
    #         if request.env['res.users'].sudo().search([('login', '=', email)]):
    #             return jwt_request.response(status=400, data={'message': 'Email address is not available'})
    #         user = request.env['res.users'].sudo().create({
    #             'login': email,
    #             'password': password,
    #             'name': name,
    #             'email': email,
    #         })
    #         if user:
    #             # no need to authenticate user here
    #             # cuz we just respond data right away
    #             # if you really need to authenticate user, use jwt_request.login(email, password)
    #             # token can be used instead of password
    #             # create token
    #             token = jwt_request.create_token(user)
    #             return jwt_request.response({
    #                 'user': user.to_dict(),
    #                 'token': token
    #             })
    #     except Exception as e:
    #         _logger.error(str(e))
    #         return jwt_request.response_500({
    #             'message': 'Server error'
    #         })
    #
    # @http.route('/api/http/signup', type='http', auth='public', csrf=False, cors='*', methods=['POST'])
    # def register(self, email=None, name=None, password=None, **kw):
    #     """
    #     Sign up using auth_signup modules
    #     """
    #     if not is_valid_email(email):
    #         return jwt_request.response(status=400, data={'message': 'Invalid email address'})
    #     if not name:
    #         return jwt_request.response(status=400, data={'message': 'Name cannot be empty'})
    #     if not password:
    #         return jwt_request.response(status=400, data={'message': 'Password cannot be empty'})
    #
    #     # sign up
    #     try:
    #         model = request.env['res.users'].sudo()
    #         signup = getattr(model, 'signup')
    #         if signup:
    #             if request.env['res.users'].sudo().search([('login', '=', email)]):
    #                 return jwt_request.response(status=400, data={'message': 'Email address is not available'})
    #             data = {
    #                 'login': email,
    #                 'password': password,
    #                 'name': name,
    #                 'email': email,
    #             }
    #             # signup return a tuple (db, login, password)
    #             # you can use that to call jwt_request.login(login, password)
    #             signup(data)
    #             # but, we just need to retrieve the newly created user
    #             user = model.search([
    #                 ('login', '=', email)
    #             ])
    #             if user:
    #                 token = jwt_request.create_token(user)
    #                 return jwt_request.response({
    #                     'user': user.to_dict(),
    #                     'token': token
    #                 })
    #             raise Exception()
    #     except SignupError:
    #         return jwt_request.response({
    #             'message': 'Signup is currently disabled',
    #         }, 400)
    #     except Exception as e:
    #         _logger.error(str(e))
    #         return jwt_request.response_500({
    #             'message': 'Cannot create user'
    #         })

    def _response_auth(self, result: str):
        if result['status'] == 200:
            return jwt_request.response({
                # 'user': request.env.user.to_dict(),
                'status': result['status'],
                'message': result['message'],
                'token': result['token'],
            })
        else:
            return jwt_request.response({
                'status': result['status'],
                'message': result['message'],
                'token': '',
            })
