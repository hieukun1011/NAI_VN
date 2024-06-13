import json
from odoo import http
from odoo.http import request


class ApprovedEmail(http.Controller):

    @http.route('/approve_request/<int:id>/<string:action>', type='http', auth='public')
    def approve_request(self, id, action, **kw):
        record = request.env['hr.leave'].sudo().browse(int(id))
        window_close = """ <html>
                <head>
                    <script type="text/javascript">
                        window.onload = function() {
                            window.close();
                        };
                    </script>
                </head>
                </html>
                """
        if record:
            if action == 'approved':
                record.action_approve()
            else:
                record.action_refuse()
        return window_close
