# app/services/system_log_service.py
from app import db
from app.models.system_log_mdl import SystemLog
from flask_login import current_user
from flask import request

class SystemLogService:
    @staticmethod
    def log(action, module, description, entity_id=None, old_val=None, new_val=None):
        """
        Logs a system event.
        usage: SystemLogService.log('Update', 'Case', 'Changed status', 1, {'status':'Open'}, {'status':'Closed'})
        """
        try:
            # 1. Get User Context
            user_id = None
            if current_user and current_user.is_authenticated:
                user_id = current_user.id
            
            # 2. Get IP Context
            # Handle proxy setups (X-Forwarded-For) or direct access
            if request:
                if request.headers.getlist("X-Forwarded-For"):
                    ip = request.headers.getlist("X-Forwarded-For")[0]
                else:
                    ip = request.remote_addr
            else:
                ip = 'System/Console'

            # 3. Create Log
            new_log = SystemLog(
                user_id=user_id,
                action=action,
                module=module,
                entity_id=entity_id,
                description=description,
                old_value=old_val,
                new_value=new_val,
                ip_address=ip
            )
            
            db.session.add(new_log)
            db.session.commit()
            return True
            
        except Exception as e:
            # Failsafe: Logging failures should never crash the main application
            print(f"!!! SYSTEM LOGGING ERROR: {str(e)}")
            db.session.rollback()
            return False