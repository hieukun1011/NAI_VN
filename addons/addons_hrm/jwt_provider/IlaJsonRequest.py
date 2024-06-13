#
# import json
#
# from odoo.http import Response, JsonRequest
# from odoo.tools import date_utils
#
#
# class IlaJsonRequest(JsonRequest):
#
#     # https://stackoverflow.com/questions/62388254/in-odoos-controller-file-how-to-change-the-json-response-format-when-the-type
#     # https://stackoverflow.com/questions/805066/how-do-i-call-a-parent-classs-method-from-a-child-class-in-python
#     def _json_response(self, result=None, error=None):
#
#         # custom for api public
#         api_key = ''
#         if self.endpoint and self.endpoint.routing:
#             api_key = self.endpoint.routing.get('api_key')
#         if api_key == 'X-Sogo-Access-Token':
#             response = {}
#             if error is not None:
#                 response['error'] = error
#             if result is not None:
#                 response = result
#
#             mime = 'application/json'
#             body = json.dumps(response, default=date_utils.json_default)
#
#             return Response(
#                 body, status=error and error.pop('http_status', 200) or 200,
#                 headers=[('Content-Type', mime), ('Content-Length', len(body))]
#             )
#
#         response = {
#             'jsonrpc': '2.0',
#             'id': self.jsonrequest.get('id')
#         }
#         if error is not None:
#             response['error'] = error
#         if result is not None:
#             response['result'] = result
#
#         mime = 'application/json'
#         body = json.dumps(response, default=date_utils.json_default)
#
#         return Response(
#             body, status=error and error.pop('http_status', 200) or 200,
#             headers=[('Content-Type', mime), ('Content-Length', len(body))]
#         )
#
#     setattr(JsonRequest, '_json_response', _json_response)  # overwrite the method
