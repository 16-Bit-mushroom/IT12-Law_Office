# app/models/case_mdl.py
from . import db
from datetime import datetime, timezone, timedelta 
from app.utils.mixins import SoftDeleteMixin
import json

PHT = timezone(timedelta(hours=8))

class Case(db.Model, SoftDeleteMixin):
    __tablename__ = 'cases'
    
    id = db.Column(db.Integer, primary_key=True)
    # ... (Keep all your existing fields: case_number, title, etc.) ...
    case_number = db.Column(db.String(100), unique=True, nullable=False)
    title = db.Column(db.String(255), nullable=False)
    case_category = db.Column(db.String(50), default='individual', nullable=False)
    case_type = db.Column(db.String(100), nullable=False)
    violation = db.Column(db.String(255), nullable=True)
    cause_of_action = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(50), default='active', nullable=False)
    
    engagement_date = db.Column(db.Date, nullable=False)
    filing_date = db.Column(db.Date, nullable=True)
    
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    assigned_attorney_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(PHT))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(PHT), onupdate=lambda: datetime.now(PHT))

    # === NEW SNAPSHOT FIELD ===
    # Stores a JSON string of the client's details at the time of closing
    client_snapshot = db.Column(db.Text, nullable=True) 
    
    # Relationships
    client = db.relationship('Client', backref='cases', lazy=True)
    assigned_attorney = db.relationship('User', backref='assigned_cases', lazy=True)
    schedules = db.relationship('Schedule', backref='case', lazy=True, cascade="all, delete-orphan", order_by="asc(Schedule.deadline)")
    
    # Helper to get snapshot as dict
    @property
    def snapshot_data(self):
        if self.client_snapshot:
            try:
                return json.loads(self.client_snapshot)
            except:
                return None
        return None

    def __repr__(self):
        return f"<Case(id={self.id}, case_number='{self.case_number}')>"