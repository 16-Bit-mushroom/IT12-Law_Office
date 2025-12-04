# reminder_mdl.py - For storing reminders
from . import db
from datetime import datetime

class Reminder(db.Model):
    __tablename__ = 'reminders'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    
    # When to remind
    remind_at = db.Column(db.DateTime, nullable=False)
    
    # Priority/Urgency
    priority = db.Column(db.String(20), default='medium', nullable=False)  # 'low', 'medium', 'high', 'urgent'
    
    # Status
    status = db.Column(db.String(20), default='pending', nullable=False)  # 'pending', 'completed', 'cancelled'
    
    # Recurrence (optional)
    is_recurring = db.Column(db.Boolean, default=False, nullable=False)
    recurrence_pattern = db.Column(db.String(50), nullable=True)  # 'daily', 'weekly', 'monthly', 'yearly'
    
    # Relationships
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    related_case_id = db.Column(db.Integer, db.ForeignKey('cases.id'), nullable=True)
    related_notarial_id = db.Column(db.Integer, db.ForeignKey('notarial_entries.id'), nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    user = db.relationship('User', backref='reminders', lazy=True)
    case = db.relationship('Case', backref='reminders', lazy=True)
    notarial_entry = db.relationship('NotarialEntry', backref='reminders', lazy=True)
    
    def __repr__(self):
        return f"<Reminder(id={self.id}, title='{self.title}', remind_at='{self.remind_at}', status='{self.status}')>"
    
    @property
    def is_overdue(self):
        from datetime import datetime
        return self.remind_at < datetime.utcnow() and self.status == 'pending'