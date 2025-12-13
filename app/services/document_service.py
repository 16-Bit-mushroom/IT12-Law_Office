# app/services/document_service.py
import os
import uuid
from datetime import datetime, timezone
from werkzeug.utils import secure_filename
from flask import current_app
from app.models.document_mdl import Document
from app.models import db

class DocumentService:
    
    ALLOWED_EXTENSIONS = {
        'pdf', 'doc', 'docx', 'xls', 'xlsx', 
        'jpg', 'jpeg', 'png', 'gif', 'bmp',
        'txt', 'rtf'
    }
    
    @staticmethod
    def get_upload_folder():
        return os.path.join(current_app.root_path, 'uploads', 'documents')
    
    @staticmethod
    def allowed_file(filename):
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in DocumentService.ALLOWED_EXTENSIONS
    
    @staticmethod
    def get_documents_by_parent(parent_type, parent_id):
        return Document.query.filter_by(
            parent_type=parent_type, 
            parent_id=parent_id
        ).filter(Document.deleted_at == None).order_by(
            # Sort: Lacking items first, then by date
            db.case((Document.document_status == 'Lacking', 1), else_=2),
            Document.uploaded_at.desc()
        ).all()
    
    # --- NEW: Create Placeholder ---
    @staticmethod
    def create_requirement(parent_type, parent_id, document_type, notes=None, user_id=None):
        """Creates a placeholder for a missing document"""
        try:
            document = Document(
                filename=f"[MISSING] {document_type}", # Placeholder name
                file_path='PENDING_UPLOAD',  # Dummy path
                file_type=None,
                file_size=0,
                document_type=document_type,
                document_status='Lacking', # The key status
                notes=notes,
                parent_type=parent_type,
                parent_id=parent_id,
                uploaded_by=user_id
            )
            
            db.session.add(document)
            db.session.commit()
            return document
        except Exception as e:
            db.session.rollback()
            raise e

    # --- UPDATED: Handle Fulfillment ---
    @staticmethod
    def create_document(file, parent_type, parent_id, document_type=None, notes=None, user_id=None, document_id=None):
        try:
            if not file or file.filename == '':
                raise ValueError("No file selected")
            
            if not DocumentService.allowed_file(file.filename):
                raise ValueError("File type not allowed")
            
            # 1. Setup Paths
            upload_folder = DocumentService.get_upload_folder()
            os.makedirs(upload_folder, exist_ok=True)
            
            # 2. Generate Filename
            original_filename = secure_filename(file.filename)
            file_extension = os.path.splitext(original_filename)[1]
            unique_filename = f"{uuid.uuid4().hex}{file_extension}"
            file_path = os.path.join(upload_folder, unique_filename)
            
            # 3. Save File
            file.save(file_path)
            
            # 4. Save/Update DB Record
            if document_id:
                # FULFILL EXISTING REQUIREMENT
                document = Document.query.get(document_id)
                if document:
                    document.filename = original_filename
                    document.file_path = file_path
                    document.file_type = file_extension[1:].lower() if file_extension else None
                    document.file_size = os.path.getsize(file_path)
                    document.document_status = 'Pending Review' # Change status
                    document.uploaded_at = datetime.now(timezone.utc) # Update time
                    if notes: document.notes = notes # Update notes if provided
            else:
                # CREATE NEW DOCUMENT
                document = Document(
                    filename=original_filename,
                    file_path=file_path,
                    file_type=file_extension[1:].lower() if file_extension else None,
                    file_size=os.path.getsize(file_path),
                    document_type=document_type,
                    document_status='Pending Review',
                    notes=notes,
                    parent_type=parent_type,
                    parent_id=parent_id,
                    uploaded_by=user_id
                )
                db.session.add(document)

            db.session.commit()
            return document
            
        except Exception as e:
            db.session.rollback()
            if 'file_path' in locals() and os.path.exists(file_path):
                os.remove(file_path)
            raise e
    
    @staticmethod
    def delete_document(document_id):
        try:
            document = Document.query.get(document_id)
            if not document:
                return False
            document.soft_delete() 
            return True
        except Exception as e:
            db.session.rollback()
            raise e
            
    @staticmethod
    def get_document_count_by_parent(parent_type, parent_id):
        return Document.query.filter_by(
            parent_type=parent_type, 
            parent_id=parent_id
        ).count()

    @staticmethod
    def update_document_details(document_id, document_type, notes):
        """Updates the type/title and notes of a document/requirement"""
        try:
            document = Document.query.get(document_id)
            if document:
                document.document_type = document_type
                document.notes = notes
                db.session.commit()
                return True
            return False
        except Exception as e:
            db.session.rollback()
            raise e
    @staticmethod
    def approve_document(document_id, user_id):
        document = Document.query.get(document_id)
        if document:
            document.document_status = 'Approved'
            document.notes = f"Approved by Admin on {datetime.now().strftime('%Y-%m-%d')}"
            db.session.commit()
            return True
        return False

    @staticmethod
    def reject_document(document_id, reason):
        document = Document.query.get(document_id)
        if document:
            document.document_status = 'Lacking' # Revert to missing/lacking
            # Append rejection reason to notes
            old_note = document.notes or ""
            document.notes = f"REJECTED: {reason}. {old_note}"
            # Optional: Delete the file_path if you want to force re-upload, 
            # but keeping it for reference is usually better.
            db.session.commit()
            return True
        return False