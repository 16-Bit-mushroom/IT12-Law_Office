from . import db
from datetime import datetime
from app.utils.mixins import SoftDeleteMixin
import os

class Document(db.Model, SoftDeleteMixin):
    __tablename__ = 'documents'
    
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_type = db.Column(db.String(50), nullable=True)
    file_size = db.Column(db.Integer, nullable=True)  # in bytes
    document_type = db.Column(db.String(100), nullable=True)  # e.g., Affidavit, ID, SPA Draft, etc.
    notes = db.Column(db.Text, nullable=True)
    
    # === NEW FIELDS FOR TRACKING ===
    # Tracks the status/progress of the document (e.g., Draft, For Signature, Complete, Lacking)
    document_status = db.Column(db.String(50), default='Pending', nullable=False) 
    
    # Tracks where the physical copy of the document is stored
    # physical_location = db.Column(db.String(255), nullable=True) 
    # ===============================
    
    # Parent reference (polymorphic)
    parent_type = db.Column(db.String(50), nullable=False)  # 'notarial_entry', 'case', 'client'
    parent_id = db.Column(db.Integer, nullable=False)
    
    # Metadata
    uploaded_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_modified = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    uploader = db.relationship('User', backref='uploaded_documents', lazy=True)

    # ... (rest of model and property methods remain the same) ...

    def __repr__(self):
        return f"<Document(id={self.id}, filename='{self.filename}', parent='{self.parent_type}:{self.parent_id}')>"

    @property
    def file_extension(self):
        return os.path.splitext(self.filename)[1].lower() if self.filename else ''

    @property
    def formatted_file_size(self):
        if not self.file_size:
            return "Unknown"
        for unit in ['B', 'KB', 'MB', 'GB']:
            if self.file_size < 1024.0:
                return f"{self.file_size:.1f} {unit}"
            self.file_size /= 1024.0
        return f"{self.file_size:.1f} TB"

    @property
    def icon_class(self):
        ext = self.file_extension
        if ext in ['.pdf']:
            return 'file-pdf'
        elif ext in ['.doc', '.docx']:
            return 'file-word'
        elif ext in ['.xls', '.xlsx']:
            return 'file-excel'
        elif ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp']:
            return 'file-image'
        else:
            return 'file'