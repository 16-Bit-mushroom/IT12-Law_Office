# notarial_entries_routes.py
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from app.models.notarial_entry_mdl import NotarialEntry
from app.models import db
from app.services.notarial_entry_service import NotarialEntryService
from datetime import datetime
from sqlalchemy.orm import joinedload
from app.utils.permissions import staff_or_admin_required
from app.services.system_log_service import SystemLogService

# --- NEW IMPORTS FOR SUGGESTIONS ---
from app.services.suggestion_service import SuggestionService
from app.models.suggestion_mdl import Suggestion
# -----------------------------------

notarial_entries_bp = Blueprint('notarial_entries', __name__, url_prefix='/notarial-entries')

@notarial_entries_bp.route('/')
@staff_or_admin_required
@login_required
def notarial_entries_page():
    """Display all notarial entries"""
    entries = NotarialEntryService.get_all_entries()
    return render_template('notarial_entries.html', entries=entries, now=datetime.utcnow())

@notarial_entries_bp.route('/<int:entry_id>')
@staff_or_admin_required
@login_required
def entry_details(entry_id):
    """Display notarial entry details and documents"""
    entry = NotarialEntryService.get_entry_by_id(entry_id)
    if not entry:
        flash('Notarial entry not found!', 'error')
        return redirect(url_for('notarial_entries.notarial_entries_page'))
    
    # Load documents for this entry
    from app.services.document_service import DocumentService
    documents = DocumentService.get_documents_by_parent('notarial_entry', entry_id)
    
    return render_template('notarial_entry_details.html', 
                         entry=entry, 
                         documents=documents,
                         now=datetime.utcnow())

@notarial_entries_bp.route('/<int:entry_id>/json', methods=['GET'])
@staff_or_admin_required
@login_required
def get_entry_json(entry_id):
    """Get notarial entry data for editing (JSON API)"""
    entry = NotarialEntry.query.options(
        joinedload(NotarialEntry.parties),
        joinedload(NotarialEntry.witnesses)
    ).get(entry_id)
    
    if entry:
        return jsonify({
            'id': entry.id,
            'not_entry_num': entry.not_entry_num,
            'not_page_num': entry.not_page_num,
            'not_book_num': entry.not_book_num,
            'not_series': entry.not_series,
            'not_title': entry.not_title,
            'not_date': entry.not_date.strftime('%Y-%m-%dT%H:%M'),
            'not_type_act': entry.not_type_act,
            'not_fee': float(entry.not_fee),
            'not_fee_or': entry.not_fee_or,
            'not_other_place': entry.not_other_place,
            'not_comp_evidence_id': entry.not_comp_evidence_id,
            'id_expiration_date': entry.parties[0].party_id_expiry.strftime('%Y-%m-%d') if entry.parties and entry.parties[0].party_id_expiry else None,
            'parties': [{
                'id': party.id,
                'party_name': party.party_name,
                'party_address': party.party_address,
                'party_id_type': party.party_id_type,
                'party_id_number': party.party_id_number,
                'party_id_expiry': party.party_id_expiry.strftime('%Y-%m-%d') if party.party_id_expiry else None
            } for party in entry.parties],
            'witnesses': [{
                'id': witness.id,
                'witness_name': witness.witness_name,
                'witness_address': witness.witness_address
            } for witness in entry.witnesses]
        })
    return jsonify({'error': 'Entry not found'}), 404

@notarial_entries_bp.route('/<int:entry_id>/mark-paid', methods=['POST'])
@staff_or_admin_required
@login_required
def mark_as_paid(entry_id):
    try:
        or_number = request.form.get('or_number', '')
        entry = NotarialEntryService.mark_as_paid(entry_id, or_number)
        if entry:
            SystemLogService.log(
                action='Payment',
                module='Notarial',
                description=f"Notarial Entry #{entry.not_entry_num} marked as PAID. OR: {or_number}",
                entity_id=entry.id,
                new_val={'payment_status': 'Paid', 'or_number': or_number}
            )
            if or_number:
                flash(f'Entry marked as paid with OR# {or_number}!', 'success')
            else:
                flash('Entry marked as paid! (No OR number provided)', 'warning')
        else:
            flash('Entry not found!', 'error')
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
    return redirect(url_for('notarial_entries.notarial_entries_page'))

# =======================================================
#  SMART SUGGESTIONS API (ADDED)
# =======================================================

@notarial_entries_bp.route('/api/suggestions/<field>', methods=['GET'])
@staff_or_admin_required
@login_required
def get_suggestions_api(field):
    """Get top suggestions for a field"""
    suggestions = SuggestionService.get_suggestions('notarial', field)
    return jsonify(suggestions)

@notarial_entries_bp.route('/api/suggestions/<field>/search', methods=['GET'])
@staff_or_admin_required
@login_required
def search_suggestions_api(field):
    """Search suggestions for a field"""
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify([])
    
    # Direct query to find matching suggestions
    suggestions = Suggestion.query.filter(
        Suggestion.module == 'notarial',
        Suggestion.suggestion_type == field,
        Suggestion.value.ilike(f'%{query}%'),
        Suggestion.is_active == True
    ).order_by(Suggestion.use_count.desc()).limit(10).all()
    
    return jsonify([s.value for s in suggestions])

@notarial_entries_bp.route('/api/suggestions/<field>/remove', methods=['POST'])
@staff_or_admin_required
@login_required
def remove_suggestion_api(field):
    """Remove a suggestion"""
    data = request.get_json()
    value = data.get('value')
    
    if SuggestionService.remove_suggestion('notarial', field, value):
        return jsonify({'message': 'Suggestion removed'})
    return jsonify({'error': 'Failed to remove suggestion'}), 400


# =======================================================
#  CREATE & UPDATE (With Learning Logic)
# =======================================================

@notarial_entries_bp.route('/create-manual', methods=['POST'])
@staff_or_admin_required
@login_required
def create_manual_entry():
    """Create a manual notarial entry and auto-create transaction"""
    try:
        # Create the entry
        entry = NotarialEntryService.create_manual_entry(request.form, current_user.id)
        
        # --- LEARN NEW INPUTS ---
        # Document Title
        if request.form.get('document_title'):
            SuggestionService.add_suggestion('notarial', 'document_title', request.form['document_title'])
        # Notarial Act Type
        if request.form.get('notarial_act_type'):
            SuggestionService.add_suggestion('notarial', 'notarial_act', request.form['notarial_act_type'])
        # Other Place
        if request.form.get('other_place'):
            SuggestionService.add_suggestion('notarial', 'other_place', request.form['other_place'])
        # Dynamic Party IDs (Iterate through form list)
        if 'party_id_type' in request.form:
            # Handle multiple values for the same key
            id_types = request.form.getlist('party_id_type')
            for id_type in id_types:
                if id_type:
                    SuggestionService.add_suggestion('notarial', 'party_id', id_type)
        # ------------------------

        SystemLogService.log('Create', 'Notarial', f"Created Notarial Entry #{entry.not_entry_num}", entry.id)
        
        flash('Notarial entry created successfully!', 'success')
        return redirect(url_for('notarial_entries.notarial_entries_page'))
        
    except Exception as e:
        flash(f'Error creating notarial entry: {str(e)}', 'error')
        return redirect(url_for('notarial_entries.notarial_entries_page'))

@notarial_entries_bp.route('/<int:entry_id>/update', methods=['POST'])
@staff_or_admin_required
@login_required
def update_entry(entry_id):
    """Update a notarial entry"""
    try:
        old_entry = NotarialEntryService.get_entry_by_id(entry_id)
        old_fee = str(old_entry.not_fee) if old_entry else None
        
        entry = NotarialEntryService.update_entry(entry_id, request.form, current_user.id)
        
        if entry:
            # --- LEARN NEW INPUTS (Update) ---
            if request.form.get('document_title'):
                SuggestionService.add_suggestion('notarial', 'document_title', request.form['document_title'])
            if request.form.get('notarial_act_type'):
                SuggestionService.add_suggestion('notarial', 'notarial_act', request.form['notarial_act_type'])
            if request.form.get('other_place'):
                SuggestionService.add_suggestion('notarial', 'other_place', request.form['other_place'])
            if 'party_id_type' in request.form:
                id_types = request.form.getlist('party_id_type')
                for id_type in id_types:
                    if id_type:
                        SuggestionService.add_suggestion('notarial', 'party_id', id_type)
            # ---------------------------------

            new_fee = str(entry.not_fee)
            desc = f"Updated Notarial Entry #{entry.not_entry_num}"
            if old_fee != new_fee:
                desc += f" (Fee changed: {old_fee} -> {new_fee})"
                
            SystemLogService.log('Update', 'Notarial', desc, entry.id)
            
            flash('Notarial entry updated successfully!', 'success')
        else:
            flash('Notarial entry not found!', 'error')
        return redirect(url_for('notarial_entries.notarial_entries_page'))
        
    except Exception as e:
        flash(f'Error updating notarial entry: {str(e)}', 'error')
        return redirect(url_for('notarial_entries.notarial_entries_page'))

@notarial_entries_bp.route('/<int:entry_id>/delete', methods=['POST'])
@staff_or_admin_required
@login_required
def delete_entry(entry_id):
    """Delete a notarial entry"""
    try:
        success = NotarialEntryService.delete_entry(entry_id)
        if success:
            flash('Notarial entry deleted successfully!', 'success')
        else:
            flash('Notarial entry not found!', 'error')
        return redirect(url_for('notarial_entries.notarial_entries_page'))
    except Exception as e:
        flash(f'Error deleting notarial entry: {str(e)}', 'error')
        return redirect(url_for('notarial_entries.notarial_entries_page'))

# --- HELPER ROUTES ---

@notarial_entries_bp.route('/last-entry')
@staff_or_admin_required
@login_required
def get_last_entry():
    """Get last used book, page, entry numbers"""
    last_entry = NotarialEntryService.get_last_entry_values(current_user.id)
    return jsonify(last_entry)

@notarial_entries_bp.route('/increment-entry')
@staff_or_admin_required
@login_required
def increment_entry():
    """Increment entry number and return new values"""
    new_values = NotarialEntryService.increment_last_entry(current_user.id)
    return jsonify(new_values)

@notarial_entries_bp.route('/<int:entry_id>/print')
@staff_or_admin_required
@login_required
def print_entry(entry_id):
    """Print notarial entry details"""
    from app.services.print_service import PrintService
    print_data = PrintService.generate_notarial_print_data(entry_id)
    
    if not print_data:
        flash('Notarial entry not found!', 'error')
        return redirect(url_for('notarial_entries.notarial_entries_page'))
    
    # Add prepared_by from current user
    print_data['prepared_by'] = current_user.full_name if hasattr(current_user, 'full_name') else current_user.username
    
    return render_template('notarial_entry_print.html', **print_data)