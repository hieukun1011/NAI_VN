from datetime import datetime
from pytz import timezone

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

class LogUtil(object):

    def create_log_history_partner(self, action=False, location=False, description=False):
        if self and action:
            try:
                insert_history = {
                    'partner_id': self.id,
                    'action_id': action.id,
                    'location': location,
                    'description': description if description else '',
                    'create_date': datetime.now(),
                }
                query_insert_history = '''
                                INSERT INTO history_contact (partner_id, action_id, location, description, create_date)
                                VALUES (
                                    %(partner_id)s, %(action_id)s, %(location)s, %(description)s, %(create_date)s
                                ) 
                            '''
                self.env.cr.execute(query_insert_history, insert_history)
            except Exception as e:
                print(e)
                raise e




