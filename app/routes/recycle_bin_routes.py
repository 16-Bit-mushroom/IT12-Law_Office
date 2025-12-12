from flask import Blueprint, jsonify, request
from flask_login import login_required
from app.utils.permissions import admin_required
from app.models import db
from app.models.case_mdl import Case
from app.models.client_mdl import Client
from app.models.document_mdl import Document
from app.models.notarial_entry_mdl import NotarialEntry
import os

recycle_bp = Blueprint('recycle', __name__, url_prefix='/recycle-bin')

@recycle_bp.route('/data')
@login_required
@admin_required
def get_data():
    """Fetch all deleted items based on category tab"""
    category = request.args.get('category', 'all')
    items = []

    # 1. CLIENTS
    if category in ['all', 'clients']:
        # Fetch clients where deleted_at IS NOT None
        clients = Client.query.filter(Client.deleted_at != None).all()
        for c in clients:
            items.append({
                'id': c.id,
                'type': 'Client',
                'type_slug': 'client', # Used for API calls
                'title': c.full_name,
                'subtitle': c.client_email or 'No email',
                'deleted_at': c.deleted_at.strftime('%Y-%m-%d %I:%M %p'),
                'view_url': f'/clients/{c.id}' 
            })

    # 2. CASES
    if category in ['all', 'cases']:
        cases = Case.query.filter(Case.deleted_at != None).all()
        for c in cases:
            items.append({
                'id': c.id,
                'type': 'Case',
                'type_slug': 'case',
                'title': f"Case #{c.case_number}",
                'subtitle': c.title,
                'deleted_at': c.deleted_at.strftime('%Y-%m-%d %I:%M %p'),
                'view_url': f'/cases/{c.id}' 
            })

    # 3. DOCUMENTS
    if category in ['all', 'documents']:
        docs = Document.query.filter(Document.deleted_at != None).all()
        for d in docs:
            items.append({
                'id': d.id,
                'type': 'Document',
                'type_slug': 'document',
                'title': d.filename,
                'subtitle': d.document_type or 'General File',
                'deleted_at': d.deleted_at.strftime('%Y-%m-%d %I:%M %p'),
                'view_url': f'/documents/download/{d.id}'
            })

    # 4. NOTARIAL
    if category in ['all', 'notarial']:
        entries = NotarialEntry.query.filter(NotarialEntry.deleted_at != None).all()
        for e in entries:
            items.append({
                'id': e.id,
                'type': 'Notarial',
                'type_slug': 'entry',
                'title': f"Entry {e.not_book_num}-{e.not_page_num}-{e.not_entry_num}",
                'subtitle': e.not_title,
                'deleted_at': e.deleted_at.strftime('%Y-%m-%d %I:%M %p'),
                'view_url': f'/notarial-entries/{e.id}'
            })

    # Sort: Most recently deleted first
    items.sort(key=lambda x: x['deleted_at'], reverse=True)
    
    return jsonify(items)

@recycle_bp.route('/restore/<type>/<int:id>', methods=['POST'])
@login_required
@admin_required
def restore_item(type, id):
    """Restores an item by setting deleted_at = NULL"""
    model_map = {
        'client': Client,
        'case': Case,
        'document': Document,
        'entry': NotarialEntry
    }
    
    if type in model_map:
        item = model_map[type].query.get(id)
        if item:
            item.restore() # Calls the Mixin method
            return jsonify({'success': True})
            
    return jsonify({'error': 'Item not found'}), 404

@recycle_bp.route('/purge/<type>/<int:id>', methods=['POST'])
@login_required
@admin_required
def purge_item(type, id):
    """Permanently deletes an item from the database"""
    try:
        item = None
        
        # We need specific logic per type to clean up related data (like files)
        if type == 'client': 
            item = Client.query.get(id)
        elif type == 'case': 
            item = Case.query.get(id)
        elif type == 'entry': 
            item = NotarialEntry.query.get(id)
            # Manually delete parties/witnesses first to avoid FK errors
            if item:
                from app.models.notarial_entry_mdl import NotarialEntryParty, NotarialEntryWitness
                NotarialEntryParty.query.filter_by(notarial_entry_id=item.id).delete()
                NotarialEntryWitness.query.filter_by(notarial_entry_id=item.id).delete()
                
        elif type == 'document': 
            item = Document.query.get(id)
            # Delete physical file from disk
            if item and item.file_path and os.path.exists(item.file_path):
                try: os.remove(item.file_path)
                except: pass

        if item:
            db.session.delete(item) # Hard delete
            db.session.commit()
            return jsonify({'success': True})
        
        return jsonify({'error': 'Item not found'}), 404
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500