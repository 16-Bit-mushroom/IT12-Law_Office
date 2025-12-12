# app/models/system_log_mdl.py
from . import db
from datetime import datetime, timezone, timedelta

# Define PHT
PHT = timezone(timedelta(hours=8))

class SystemLog(db.Model):
    __tablename__ = 'system_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # Classification
    action = db.Column(db.String(50), nullable=False)
    module = db.Column(db.String(50), nullable=False)
    
    # Entity Reference
    entity_id = db.Column(db.Integer, nullable=True)
    
    # Description
    description = db.Column(db.String(255), nullable=False)
    
    # Audit Trail
    old_value = db.Column(db.JSON, nullable=True) 
    new_value = db.Column(db.JSON, nullable=True)
    
    # Metadata
    ip_address = db.Column(db.String(50), nullable=True)
    
    # UPDATED: Use PHT default
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(PHT))

    # Relationship
    user = db.relationship('User', backref='logs', lazy=True)

    def __repr__(self):
        return f"<Log {self.action} - {self.module}>"