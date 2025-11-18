# notarial_entries_routes.py - CORRECTED
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required
from app.models.notarial_entry_mdl import NotarialEntry, NotarialEntryParty, NotarialEntryWitness
from app.models import db
from app.services.notarial_entry_service import NotarialEntryService
from datetime import datetime
from sqlalchemy.orm import joinedload

notarial_entries_bp = Blueprint('notarial_entries', __name__, url_prefix='/notarial-entries')

@notarial_entries_bp.route('/')
@login_required
def notarial_entries_page():
    """Display all notarial entries"""
    entries = NotarialEntryService.get_all_entries()
    return render_template('notarial_entries.html', entries=entries, now=datetime.utcnow())

@notarial_entries_bp.route('/create-manual', methods=['POST'])
@login_required
def create_manual_entry():
    """Create a manual notarial entry"""
    try:
        entry = NotarialEntryService.create_manual_entry(request.form)
        flash('Notarial entry created successfully!', 'success')
        return redirect(url_for('notarial_entries.notarial_entries_page'))
        
    except Exception as e:
        flash(f'Error creating notarial entry: {str(e)}', 'error')
        return redirect(url_for('notarial_entries.notarial_entries_page'))

@notarial_entries_bp.route('/<int:entry_id>/update', methods=['POST'])
@login_required
def update_entry(entry_id):
    """Update a notarial entry"""
    try:
        entry = NotarialEntryService.update_entry(entry_id, request.form)
        if entry:
            flash('Notarial entry updated successfully!', 'success')
        else:
            flash('Notarial entry not found!', 'error')
        return redirect(url_for('notarial_entries.notarial_entries_page'))
        
    except Exception as e:
        flash(f'Error updating notarial entry: {str(e)}', 'error')
        return redirect(url_for('notarial_entries.notarial_entries_page'))

@notarial_entries_bp.route('/<int:entry_id>/delete', methods=['POST'])
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

@notarial_entries_bp.route('/<int:entry_id>', methods=['GET'])
@login_required
def get_entry(entry_id):
    """Get notarial entry data for editing"""
    # Eager load the relationships
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
            'parties': [{
                'id': party.id,
                'party_name': party.party_name,
                'party_address': party.party_address
            } for party in entry.parties],
            'witnesses': [{
                'id': witness.id,
                'witness_name': witness.witness_name,
                'witness_address': witness.witness_address
            } for witness in entry.witnesses]
        })
    return jsonify({'error': 'Entry not found'}), 404