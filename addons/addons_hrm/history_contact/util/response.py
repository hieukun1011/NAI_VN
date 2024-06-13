"""Part of odoo. See LICENSE file for full copyright and licensing details."""
import logging
from datetime import datetime

import pytz
from odoo import _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


def convert_time_to_utc(dt, tz_name=None):
    """
    @param dt: datetime obj to convert to UTC
    @param tz_name: the name of the timezone to convert. In case of no tz_name passed, this method will try to find the timezone in context or the login user record

    @return: an instance of datetime object
    """
    if dt:
        dt = datetime.strptime(dt, '%Y-%m-%d %H:%M:%S')
    tz_name = 'Asia/Bangkok'
    # tz_name = tz_name or request.env.context.get('tz') or request.env.user.tz
    if not tz_name:
        raise ValidationError(
            _("Local time zone is not defined. You may need to set a time zone in your user's Preferences."))
    local = pytz.timezone(tz_name)
    local_dt = local.localize(dt, is_dst=None)
    return local_dt.astimezone(pytz.utc)


def check_field_require(field_require={}, payload={}):
    for field in field_require:
        if field not in payload.keys() or (
                type(payload.get(field)) != int and payload.get(field).replace(' ', '') == ''):
            result = {"status": 400, "message": "Data invalid! %s is required!!!" % field_require[field]}
            return result
    return ''


def response_500(exception=None, message=None):
    return {
        'status': 500,
        'message': exception or 'Server error',
        'detail': message or "None"
    }


def response_400(message):
    return {
        'status': 400,
        'message': message
    }


def response_200(message=None, data=None):
    return {
        'status': 200,
        'message': message or 'SUCCESS!',
        'data': data or 'None'
    }
