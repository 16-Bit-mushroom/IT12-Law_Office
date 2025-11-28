# models/representative_mdl.py
from . import db
from datetime import datetime

class Representative(db.Model):
    __tablename__ = 'representatives'
    
    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer, db.ForeignKey('cases.id'), nullable=False)
    full_name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=True)
    phone = db.Column(db.String(50), nullable=True)
    role = db.Column(db.String(100), nullable=True)  # e.g., primary contact, legal rep, etc.
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    case = db.relationship('Case', backref='representatives', lazy=True)
    
    def __repr__(self):
        return f"<Representative(id={self.id}, full_name='{self.full_name}', case_id={self.case_id})>"