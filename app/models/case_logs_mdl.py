from . import db
from datetime import datetime

class CaseDocument(db.Model):
    __tablename__ = 'case_documents'
    
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_type = db.Column(db.String(50), nullable=True)
    file_size = db.Column(db.Integer, nullable=True)
    document_type = db.Column(db.String(100), nullable=True)
    document_status = db.Column(db.String(50), default='Pending', nullable=False)
    notes = db.Column(db.Text, nullable=True)
    
    # Foreign Keys
    case_id = db.Column(db.Integer, db.ForeignKey('cases.id'), nullable=False)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # Metadata
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<CaseDocument(id={self.id}, filename='{self.filename}', case_id={self.case_id})>"