from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required
from app.models.notarial_entry_mdl import NotarialEntry
from app.models import db
from datetime import datetime

notarial_entries_bp = Blueprint('notarial_entries', __name__, url_prefix='/notarial-entries')

@notarial_entries_bp.route('/')
@login_required
def notarial_entries_page():
    """Display all notarial entries"""
    entries = NotarialEntry.query.order_by(NotarialEntry.not_date.desc()).all()
    return render_template('notarial_entries.html', entries=entries, now=datetime.utcnow())

@notarial_entries_bp.route('/create-manual', methods=['POST'])
@login_required
def create_manual_entry():
    """Create a manual notarial entry"""
    try:
        entry = NotarialEntry(
            not_entry_num=request.form['entry_number'],
            not_date=datetime.strptime(request.form['notarization_date'], '%Y-%m-%dT%H:%M'),
            notarial_act_type=request.form['notarial_act_type'],
            not_title=request.form['document_title'],
            not_party_name=request.form['principal_name'],
            principal_address=request.form['principal_address'],
            personal_knowledge=bool(request.form.get('personal_knowledge')),
            id_type=request.form.get('id_type'),
            id_number=request.form.get('id_number'),
            id_issuing_agency=request.form.get('issuing_agency'),
            id_date_issued=datetime.strptime(request.form['id_date_issued'], '%Y-%m-%d').date() if request.form.get('id_date_issued') else None,
            not_witness_name=request.form.get('witness_name'),
            witness_address=request.form.get('witness_address'),
            special_remarks=request.form.get('special_remarks'),
            physical_book_signed=bool(request.form.get('physical_book_signed')),
            thumbprint_obtained=bool(request.form.get('thumbprint_obtained'))
        )
        
        db.session.add(entry)
        db.session.commit()
        flash('Notarial entry created successfully!', 'success')
        return redirect(url_for('notarial_entries.notarial_entries_page'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error creating notarial entry: {str(e)}', 'error')
        return redirect(url_for('notarial_entries.notarial_entries_page'))

@notarial_entries_bp.route('/<int:entry_id>/mark-signed', methods=['POST'])
@login_required
def mark_entry_signed(entry_id):
    """Mark an entry as signed in physical register"""
    try:
        entry = NotarialEntry.query.get(entry_id)
        if entry:
            entry.physical_book_signed = True
            entry.thumbprint_obtained = True
            db.session.commit()
            return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'Entry not found'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})