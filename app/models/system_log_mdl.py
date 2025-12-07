# app/models/system_log_mdl.py
from . import db
from datetime import datetime

class SystemLog(db.Model):
    __tablename__ = 'system_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # Classification
    action = db.Column(db.String(50), nullable=False)   # e.g., 'Update', 'Create', 'Login', 'Restore'
    module = db.Column(db.String(50), nullable=False)   # e.g., 'Case', 'Client', 'Notarial', 'Document'
    
    # Entity Reference
    entity_id = db.Column(db.Integer, nullable=True)    # ID of the specific item (Case ID, Client ID)
    
    # Description
    description = db.Column(db.String(255), nullable=False) # Human readable summary
    
    # Audit Trail (The "Attorney-Ready" part)
    # Stores dictionaries as JSON: {'status': 'Pending'} -> {'status': 'Active'}
    old_value = db.Column(db.JSON, nullable=True) 
    new_value = db.Column(db.JSON, nullable=True)
    
    # Metadata
    ip_address = db.Column(db.String(50), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship
    user = db.relationship('User', backref='logs', lazy=True)

    def __repr__(self):
        return f"<Log {self.action} - {self.module}>"