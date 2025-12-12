# app/models/schedule_mdl.py
from . import db
from datetime import datetime, timezone, timedelta



PHT = timezone(timedelta(hours=8))


class Schedule(db.Model):
    __tablename__ = 'schedules'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    details = db.Column(db.Text, nullable=True)  # <-- NEW FIELD
    deadline = db.Column(db.Date, nullable=False)
    priority = db.Column(db.String(20), default='normal') 
    is_done = db.Column(db.Boolean, default=False)
    
    case_id = db.Column(db.Integer, db.ForeignKey('cases.id'), nullable=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship to history
    history = db.relationship('ScheduleHistory', backref='schedule', lazy=True, order_by="desc(ScheduleHistory.created_at)")
    
    
class ScheduleHistory(db.Model):
    __tablename__ = 'schedule_history'
    
    id = db.Column(db.Integer, primary_key=True)
    schedule_id = db.Column(db.Integer, db.ForeignKey('schedules.id'), nullable=False)
    
    previous_deadline = db.Column(db.Date, nullable=False)
    new_deadline = db.Column(db.Date, nullable=False)
    reason = db.Column(db.String(255), nullable=True)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(PHT))