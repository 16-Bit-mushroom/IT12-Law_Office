# app/routes/documents_routes.py

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, send_file
from flask_login import login_required, current_user
from app.models.document_mdl import Document
from app.models.notarial_entry_mdl import NotarialEntry
# You need to import your Case/Client models here
# from app.models.case_mdl import Case 
# from app.models.client_mdl import Client 
# from app.models.consultation_mdl import Consultation
from app.services.document_service import DocumentService
from sqlalchemy import or_
import os

documents_bp = Blueprint('documents', __name__, url_prefix='/documents')

@documents_bp.route('/')
@login_required
def documents_page():
    """Display all documents with context (Client Name / Party Name)"""
    document_type = request.args.get('type', 'all')
    
    query = Document.query
    
    # Filter logic
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

        # 2. HANDLE CASES (Assumes you have a Case model linked to Client)
        elif doc.parent_type == 'case':
            # EXAMPLE LOGIC - Adjust based on your actual Case model
            # case = Case.query.get(doc.parent_id)
            # if case and case.client:
            #     doc.context_name = f"{case.client.first_name} {case.client.last_name}"
            #     doc.context_ref = f"Case #{case.case_number}"
            pass # Remove this pass when you uncomment above

        # 3. HANDLE CONSULTATIONS
        elif doc.parent_type == 'consultation':
            # consultation = Consultation.query.get(doc.parent_id)
            # if consultation:
            #     doc.context_name = consultation.client_name # Or however you store it
            pass

        # 4. HANDLE DIRECT CLIENT FILES
        elif doc.parent_type == 'client':
            # client = Client.query.get(doc.parent_id)
            # if client:
            #     doc.context_name = f"{client.first_name} {client.last_name}"
            pass
            
    return render_template('documents_page.html', 
                         documents=documents, 
                         current_filter=document_type,
                         search_term=search_term)


@documents_bp.route('/notarial-entry/<int:entry_id>')
@login_required
def notarial_entry_documents(entry_id):
    """Display documents for a specific notarial entry"""
    entry = NotarialEntryService.get_entry_by_id(entry_id)
    if not entry:
        flash('Notarial entry not found!', 'error')
        return redirect(url_for('notarial_entries.notarial_entries_page'))
    
    documents = DocumentService.get_documents_by_parent('notarial_entry', entry_id)
    return render_template('notarial_entry_details.html', 
                         entry=entry, 
                         documents=documents)

# ... rest of your routes remain the same

@documents_bp.route('/upload', methods=['POST'])
@login_required
def upload_document():
    """Upload a document"""
    try:
        file = request.files.get('file')
        parent_type = request.form.get('parent_type')
        parent_id = request.form.get('parent_id')
        document_type = request.form.get('document_type')
        notes = request.form.get('notes')
        
        if not file:
            flash('No file selected!', 'error')
            return redirect(request.referrer or url_for('notarial_entries.notarial_entries_page'))
        
        document = DocumentService.create_document(
            file=file,
            parent_type=parent_type,
            parent_id=int(parent_id),
            document_type=document_type,
            notes=notes,
            user_id=current_user.id
        )
        
        flash('Document uploaded successfully!', 'success')
        return redirect(request.referrer or url_for('notarial_entries.notarial_entries_page'))
        
    except Exception as e:
        flash(f'Error uploading document: {str(e)}', 'error')
        return redirect(request.referrer or url_for('notarial_entries.notarial_entries_page'))

@documents_bp.route('/download/<int:document_id>')
@login_required
def download_document(document_id):
    """Download a document"""
    document = Document.query.get(document_id)
    
    # Check if DB record exists
    if not document:
        flash('Document record not found!', 'error')
        return redirect(request.referrer or url_for('documents.documents_page'))

    # Check if Physical File exists
    if not document.file_path or not os.path.exists(document.file_path):
        # Optional: Logic to clean up broken DB record
        flash(f'File not found on server. It may have been moved or deleted. (Path: {document.file_path})', 'error')
        return redirect(request.referrer or url_for('documents.documents_page'))
    
    try:
        return send_file(document.file_path, 
                        as_attachment=True, 
                        download_name=document.filename)
    except Exception as e:
        flash(f'Error sending file: {str(e)}', 'error')
        return redirect(request.referrer or url_for('documents.documents_page'))

@documents_bp.route('/delete/<int:document_id>', methods=['POST'])
@login_required
def delete_document(document_id):
    """Delete a document"""
    try:
        success = DocumentService.delete_document(document_id)
        if success:
            flash('Document deleted successfully!', 'success')
        else:
            flash('Document not found!', 'error')
        return redirect(request.referrer or url_for('notarial_entries.notarial_entries_page'))
    except Exception as e:
        flash(f'Error deleting document: {str(e)}', 'error')
        return redirect(request.referrer or url_for('notarial_entries.notarial_entries_page'))

@documents_bp.route('/view/<int:document_id>')
@login_required
def view_document(document_id):
    """View a document (for images/PDFs that can be displayed in browser)"""
    document = Document.query.get(document_id)
    if not document or not os.path.exists(document.file_path):
        flash('Document not found!', 'error')
        return redirect(request.referrer or url_for('notarial_entries.notarial_entries_page'))
    
    # For now, just download. Later can implement proper viewing
    return send_file(document.file_path, 
                    as_attachment=False, 
                    download_name=document.filename)