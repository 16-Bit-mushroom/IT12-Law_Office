# app/services/system_log_service.py
from app.models import db
from app.models.system_log_mdl import SystemLog
from flask_login import current_user
from flask import request
from datetime import datetime, timezone, timedelta

# Define PHT
PHT = timezone(timedelta(hours=8))

class SystemLogService:
    
    @staticmethod
    def log(action, module, description, entity_id=None, old_val=None, new_val=None):
        """
        Logs a system event.
        """
        try:
            # 1. Get User Context
            user_id = None
            if current_user and current_user.is_authenticated:
                user_id = current_user.id
            
            # 2. Get IP Context
            ip = 'System/Console'
            if request:
                if request.headers.getlist("X-Forwarded-For"):
                    ip = request.headers.getlist("X-Forwarded-For")[0]
                else:
                    ip = request.remote_addr

            # 3. Create Log
            new_log = SystemLog(
                user_id=user_id,
                action=action,
                module=module,
                entity_id=entity_id,
                description=description,
                old_value=old_val,
                new_value=new_val,
                ip_address=ip,
                timestamp=datetime.now(PHT) # Ensure timestamp is PHT
            )
            
            db.session.add(new_log)
            db.session.commit()
            return True
            
        except Exception as e:
            print(f"!!! SYSTEM LOGGING ERROR: {str(e)}")
            db.session.rollback()
            return False

    # --- THIS WAS MISSING ---
    @staticmethod
    def get_recent_logs(limit=50):
        """Fetch recent system logs ordered by time (Newest First)"""
        return SystemLog.query.order_by(SystemLog.timestamp.desc()).limit(limit).all()

    @staticmethod
    def get_logs_by_module(module, limit=50):
        """Fetch logs for a specific module (e.g., 'Case', 'User')"""
        return SystemLog.query.filter_by(module=module)\
            .order_by(SystemLog.timestamp.desc())\
            .limit(limit).all()