# suggestion_mdl.py - For storing auto-suggestion values
from . import db
from datetime import datetime

class Suggestion(db.Model):
    __tablename__ = 'suggestions'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Module and type to categorize suggestions
    module = db.Column(db.String(50), nullable=False)  # 'notarial', 'case', 'general'
    suggestion_type = db.Column(db.String(50), nullable=False)  # 'title', 'party_id', 'notarial_act', 'book', 'page', 'entry', 'case_type', 'violation', 'cause_of_action'
    value = db.Column(db.String(255), nullable=False)
    
    # Tracking usage
    use_count = db.Column(db.Integer, default=1, nullable=False)
    last_used = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Soft delete for removing suggestions
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    # User who created/used this suggestion
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Index for faster lookups
    __table_args__ = (
        db.Index('idx_module_type', 'module', 'suggestion_type'),
    )
    
    def __repr__(self):
        return f"<Suggestion(id={self.id}, module='{self.module}', type='{self.suggestion_type}', value='{self.value}')>"