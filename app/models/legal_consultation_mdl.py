from . import db
from datetime import datetime

class LegalConsultation(db.Model):
    __tablename__ = 'legal_consultations'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Consultation Details
    consultation_type = db.Column(db.String(100), nullable=False)  # Initial, Follow-up, Emergency
    consultation_topic = db.Column(db.String(255), nullable=False)
    consultation_notes = db.Column(db.Text, nullable=False)
    consultation_duration = db.Column(db.Integer, nullable=False)  # Duration in minutes
    consultation_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Legal Analysis
    legal_issues = db.Column(db.Text)  # Key legal issues identified
    recommendations = db.Column(db.Text)  # Legal recommendations provided
    next_steps = db.Column(db.Text)  # Recommended next actions
    
    # Status
    consultation_status = db.Column(db.String(50), nullable=False, default='Completed')  # Scheduled, Completed, Cancelled
    follow_up_required = db.Column(db.Boolean, default=False)
    follow_up_date = db.Column(db.Date)
    
    # Foreign Keys
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    transaction_item_id = db.Column(db.Integer, db.ForeignKey('transaction_items.id'), nullable=True)
    
    # Relationships
    client = db.relationship('Client', backref='legal_consultations', lazy=True)
    transaction_item = db.relationship('TransactionItem', backref='legal_consultation', lazy=True)
    
    def __repr__(self):
        return f"<LegalConsultation(id={self.id}, topic='{self.consultation_topic}', client_id={self.client_id})>"