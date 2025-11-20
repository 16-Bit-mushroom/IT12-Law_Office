# services/document_service.py - FIXED PATHS
import os
import uuid
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
        """Returns the absolute path to the upload directory"""
        # This creates/finds: /home/.../IT12-Law_Office/app/uploads/documents
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
        ).order_by(Document.uploaded_at.desc()).all()
    
    @staticmethod
    def create_document(file, parent_type, parent_id, document_type=None, notes=None, user_id=None):
        try:
            if not file or file.filename == '':
                raise ValueError("No file selected")
            
            if not DocumentService.allowed_file(file.filename):
                raise ValueError("File type not allowed")
            
            # 1. Setup Paths
            upload_folder = DocumentService.get_upload_folder()
            os.makedirs(upload_folder, exist_ok=True) # Ensure directory exists
            
            # 2. Generate Filename
            original_filename = secure_filename(file.filename)
            file_extension = os.path.splitext(original_filename)[1]
            unique_filename = f"{uuid.uuid4().hex}{file_extension}"
            
            # 3. Create Absolute Path
            file_path = os.path.join(upload_folder, unique_filename)
            
            # 4. Save File
            file.save(file_path)
            
            # 5. Save DB Record
            document = Document(
                filename=original_filename,
                file_path=file_path, # Storing the absolute path is safer
                file_type=file_extension[1:].lower() if file_extension else None,
                file_size=os.path.getsize(file_path),
                document_type=document_type,
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
            # Clean up file if it was saved but DB failed
            if 'file_path' in locals() and os.path.exists(file_path):
                os.remove(file_path)
            raise e
    
    @staticmethod
    def delete_document(document_id):
        try:
            document = Document.query.get(document_id)
            if not document:
                return False
            
            # Store path before deleting DB record
            file_path = document.file_path
            
            db.session.delete(document)
            db.session.commit()
            
            # Delete physical file
            if os.path.exists(file_path):
                os.remove(file_path)
                
            return True
            
        except Exception as e:
            db.session.rollback()
            raise e
            
    # ... keep get_document_count_by_parent ...
    @staticmethod
    def get_document_count_by_parent(parent_type, parent_id):
        return Document.query.filter_by(
            parent_type=parent_type, 
            parent_id=parent_id
        ).count()