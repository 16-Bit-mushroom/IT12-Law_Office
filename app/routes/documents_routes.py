from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, send_file
from flask_login import login_required, current_user
from app.models.document_mdl import Document
from app.models.notarial_entry_mdl import NotarialEntry
from app.models.case_mdl import Case  
from app.models.client_mdl import Client  
from app.models import db 
from app.services.document_service import DocumentService
from sqlalchemy import or_
import os
from app.utils.permissions import staff_or_admin_required
from app.utils.query_filters import get_accessible_documents
from app.services.system_log_service import SystemLogService
from app.services.suggestion_service import SuggestionService

documents_bp = Blueprint('documents', __name__, url_prefix='/documents')

@documents_bp.route('/')
@staff_or_admin_required
@login_required
def documents_page():
    """Display all documents with context (Client Name / Party Name)"""
    document_type = request.args.get('type', 'all')
    
    query = Document.query
    
    # ROLE-BASED FILTERING: Staff cannot see case documents
    if current_user.role == 'staff':
        query = query.filter(Document.parent_type != 'case')
    
    # Additional filter logic
    if document_type != 'all':
        query = query.filter_by(parent_type=document_type)
    
    # Search logic
    search_term = request.args.get('search', '')
    if search_term:
        query = query.filter(or_(
            Document.filename.ilike(f'%{search_term}%'),
            Document.notes.ilike(f'%{search_term}%')
        ))
    
    documents = query.order_by(Document.uploaded_at.desc()).all()
    
    # =========================================================
    # PHASE 2 LOGIC: RESOLVE ASSOCIATED CLIENT / PARTY NAMES
    # =========================================================
    for doc in documents:
        # Set defaults
        doc.context_name = "Unknown Client" 
        doc.context_ref = f"ID: {doc.parent_id}" 

        # 1. HANDLE NOTARIAL ENTRIES
        if doc.parent_type == 'notarial_entry':
            entry = NotarialEntry.query.get(doc.parent_id)
            if entry:
                doc.context_ref = f"Entry #{entry.not_entry_num}"
                
                # Logic: Get the first party name
                if entry.parties:
                    # Get first party
                    primary_party = entry.parties[0].party_name
                    # If there are multiple parties, add "et al."
                    if len(entry.parties) > 1:
                        doc.context_name = f"{primary_party} et al."
                    else:
                        doc.context_name = primary_party
                else:
                    doc.context_name = "No Party Listed"

        # 2. HANDLE CASES - FIXED WITH ACTUAL CASE MODEL
        elif doc.parent_type == 'case':
            case = Case.query.get(doc.parent_id)
            if case:
                doc.context_ref = f"Case #{case.case_number}"
                
                # Get client name from case
                if case.client:
                    doc.context_name = f"{case.client.first_name} {case.client.last_name}"
                else:
                    doc.context_name = case.title  # Fallback to case title if no client
            else:
                doc.context_name = "Deleted Case"
                doc.context_ref = f"ID: {doc.parent_id}"

        # 3. HANDLE CONSULTATIONS
        elif doc.parent_type == 'consultation':
            # consultation = Consultation.query.get(doc.parent_id)
            # if consultation:
            #     doc.context_name = consultation.client_name # Or however you store it
            pass

        # 4. HANDLE DIRECT CLIENT FILES
        elif doc.parent_type == 'client':
            client = Client.query.get(doc.parent_id)
            if client:
                doc.context_name = f"{client.first_name} {client.last_name}"
                doc.context_ref = "Client File"
            
    return render_template('documents_page.html', 
                         documents=documents, 
                         current_filter=document_type,
                         search_term=search_term)

# ... rest of your routes remain the same

@documents_bp.route('/add-requirement', methods=['POST'])
@login_required
def add_requirement():
    """Adds a requirement OR uploads a file directly if provided"""
    try:
        # Get form data
        parent_type = request.form.get('parent_type')
        parent_id = request.form.get('parent_id')
        doc_type = request.form.get('document_type')
        notes = request.form.get('notes')
        file = request.files.get('file') # Check for file

        if file and file.filename != '':
            # CASE A: File Provided -> Create Full Document (Pending Review)
            DocumentService.create_document(
                file, parent_type, parent_id, doc_type, notes, 
                current_user.id
            )
            # Log
            from app.services.system_log_service import SystemLogService
            SystemLogService.log('Upload', 'Document', f"Added & Uploaded: {doc_type}", parent_id)
            flash('Document uploaded successfully for review', 'success')
            
        else:
            # CASE B: No File -> Create Placeholder (Lacking)
            DocumentService.create_requirement(
                parent_type, parent_id, doc_type, notes, 
                user_id=current_user.id
            )
            # Log
            from app.services.system_log_service import SystemLogService
            SystemLogService.log('Create', 'Document', f"Added requirement: {doc_type}", parent_id)
            flash('Requirement added successfully', 'success')
        
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
        
    return redirect(request.referrer or url_for('dashboard.dashboard_page'))


# documents_routes.py - Remove or redirect the duplicate route
@documents_bp.route('/notarial-entry/<int:entry_id>')
@staff_or_admin_required
@login_required
def notarial_entry_documents(entry_id):
    """Redirect to the main notarial entry details page"""
    return redirect(url_for('notarial_entries.entry_details', entry_id=entry_id))

# ... rest of your routes remain the same

@documents_bp.route('/upload', methods=['POST'])
@login_required
def upload_document():
    try:
        file = request.files.get('file')
        parent_type = request.form.get('parent_type')
        parent_id = request.form.get('parent_id')
        document_type = request.form.get('document_type')
        notes = request.form.get('notes')
        document_id = request.form.get('document_id') # For existing requirement
        
        # 1. NEW: Get Custom Status (for Notarial Archive)
        custom_status = request.form.get('custom_status') 
        
        # 2. Create the Document
        doc = DocumentService.create_document(
            file, parent_type, parent_id, document_type, notes, 
            current_user.id, document_id
        )
        
        # 3. NEW: Override Status if provided
        if custom_status:
            doc.document_status = custom_status
            # We need to import db to save this change if the service committed already
            from app.models import db 
            db.session.commit()
        
        # 4. Smart Logging
        action = "Uploaded Document"
        if document_id:
            action = "Fulfilled Requirement"
        elif custom_status == 'Archived':
            action = "Archived Document"
            
        SystemLogService.log('Upload', 'Document', f"{action}: {doc.filename}", doc.id)
        
        flash('Document saved successfully!', 'success')
        
    except Exception as e:
        flash(f'Error uploading document: {str(e)}', 'error')
        
    return redirect(request.referrer or url_for('dashboard.dashboard_page'))

@documents_bp.route('/download/<int:document_id>')
@staff_or_admin_required
@login_required
def download_document(document_id):
    """Download a document"""
    document = Document.query.get(document_id)
    
    if not document:
        flash('Document record not found!', 'error')
        return redirect(request.referrer or url_for('documents.documents_page'))

    if not document.file_path or not os.path.exists(document.file_path):
        flash(f'File not found on server. Path: {document.file_path}', 'error')
        return redirect(request.referrer or url_for('documents.documents_page'))
    
    try:
        return send_file(document.file_path, 
                        as_attachment=True, 
                        download_name=document.filename)
    except Exception as e:
        flash(f'Error sending file: {str(e)}', 'error')
        return redirect(request.referrer or url_for('documents.documents_page'))

# app/routes/documents_routes.py

@documents_bp.route('/<int:document_id>/update', methods=['POST'])
@login_required
def update_document_details(document_id):
    try:
        doc_type = request.form.get('document_type')
        notes = request.form.get('notes')
        
        DocumentService.update_document_details(document_id, doc_type, notes)
        
        # Log it
        from app.services.system_log_service import SystemLogService
        SystemLogService.log('Update', 'Document', f"Updated details for: {doc_type}", document_id)
        
        flash('Requirement details updated successfully', 'success')
    except Exception as e:
        flash(f'Error updating details: {str(e)}', 'error')
        
    return redirect(request.referrer)

@documents_bp.route('/delete/<int:document_id>', methods=['POST'])
@staff_or_admin_required
@login_required
def delete_document(document_id):
    """Delete a document"""
    try:
        doc = Document.query.get(document_id)
        filename = doc.filename if doc else 'Unknown File'
        
        success = DocumentService.delete_document(document_id)
        if success:
            SystemLogService.log('Delete', 'Document', f"Deleted file '{filename}'", document_id)
            flash('Document deleted successfully!', 'success')
        else:
            flash('Document not found!', 'error')
        return redirect(request.referrer or url_for('notarial_entries.notarial_entries_page'))
    except Exception as e:
        flash(f'Error deleting document: {str(e)}', 'error')
        return redirect(request.referrer or url_for('notarial_entries.notarial_entries_page'))

@documents_bp.route('/view/<int:document_id>')
@staff_or_admin_required
@login_required
def view_document(document_id):
    """View a document"""
    document = Document.query.get(document_id)
    if not document or not os.path.exists(document.file_path):
        flash('Document not found!', 'error')
        return redirect(request.referrer or url_for('notarial_entries.notarial_entries_page'))
    
    return send_file(document.file_path, 
                    as_attachment=False, 
                    download_name=document.filename)

@documents_bp.route('/update-status/<int:document_id>', methods=['POST'])
@staff_or_admin_required
@login_required
def update_document_status(document_id):
    """Update document status"""
    try:
        document = Document.query.get(document_id)
        if not document:
            flash('Document not found!', 'error')
            return redirect(request.referrer or url_for('documents.documents_page'))
        
        new_status = request.form.get('status')
        if new_status:
            document.document_status = new_status
            db.session.commit()
            
            # --- LOGGING ADDED ---
            filename = document.filename or document.document_type
            SystemLogService.log(
                'Update', 
                'Document', 
                f"Manual status change for '{filename}': {old_status} -> {new_status}", 
                document_id
            )
            # ---------------------
            
            flash('Document status updated successfully!', 'success')
        else:
            flash('No status provided!', 'error')
            
        return redirect(request.referrer or url_for('documents.documents_page'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating status: {str(e)}', 'error')
        return redirect(request.referrer or url_for('documents.documents_page'))

@documents_bp.route('/<int:document_id>/approve', methods=['POST'])
@login_required
def approve_document(document_id):
    # Only Admins/Lawyers should approve
    if not current_user.is_admin: # Or role check
        flash('Permission denied', 'error')
        return redirect(request.referrer)

    DocumentService.approve_document(document_id, current_user.id)
    
    # --- LOGGING ADDED ---
    doc = Document.query.get(document_id)
    title = doc.document_type or doc.filename or "Document"
    SystemLogService.log('Approve', 'Document', f"Approved: {title}", document_id)
    # -
    
    flash('Document approved', 'success')
    return redirect(request.referrer)

@documents_bp.route('/<int:document_id>/reject', methods=['POST'])
@login_required
def reject_document(document_id):
    if not current_user.is_admin:
        flash('Permission denied', 'error')
        return redirect(request.referrer)
        
    reason = request.form.get('reason', 'Invalid document')
    DocumentService.reject_document(document_id, reason)
    
    # --- LOGGING ADDED ---
    doc = Document.query.get(document_id)
    title = doc.document_type or doc.filename or "Document"
    SystemLogService.log('Reject', 'Document', f"Rejected {title}: {reason}", document_id)
    # ---------------------
    flash('Document rejected and marked as Lacking', 'warning')
    return redirect(request.referrer)