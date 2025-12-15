# notarial_entries_routes.py
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, current_app, send_file
from flask_login import login_required, current_user
from app.models.notarial_entry_mdl import NotarialEntry, NotarialEntryParty
from app.models import db
from app.services.notarial_entry_service import NotarialEntryService
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import joinedload
from app.utils.permissions import staff_or_admin_required
from app.services.system_log_service import SystemLogService

# --- NEW IMPORTS FOR SUGGESTIONS ---
from app.services.suggestion_service import SuggestionService
from app.models.suggestion_mdl import Suggestion
from docxtpl import DocxTemplate
import os
import tempfile
# -----------------------------------

notarial_entries_bp = Blueprint('notarial_entries', __name__, url_prefix='/notarial-entries')

PHT = timezone(timedelta(hours=8))

@notarial_entries_bp.route('/')
@staff_or_admin_required
@login_required
def notarial_entries_page():
    """Display all notarial entries"""
    entries = NotarialEntryService.get_all_entries()
    return render_template('notarial_entries.html', entries=entries, now=datetime.now(PHT))

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
                         now=datetime.now(PHT))

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
            
            # --- LOGGING ---
            SystemLogService.log(
                action='Delete', 
                module='Notarial', 
                description=f"Moved Notarial Entry (ID: {entry_id}) to Recycle Bin", 
                entity_id=entry_id
            )
            
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

@notarial_entries_bp.route('/<int:entry_id>/generate/<doc_type>')
@login_required
def generate_document(entry_id, doc_type):
    try:
        # 1. Load Data
        entry = NotarialEntry.query.get_or_404(entry_id)
        if not entry.parties:
            flash("No parties found in this entry.", "error")
            return redirect(request.referrer)

        # 2. Select Template
        template_filename = ""
        if doc_type == 'affidavit_loss':
            template_filename = "affidavit-of-loss-template.docx"
        elif doc_type == 'special_power_of_attorney':
            template_filename = "special-power-of-attorney.docx"
        elif doc_type == 'affidavit-of-undertaking':
            template_filename = 'affidavit-of-undertaking.docx'
        elif doc_type == 'affidavit-of-no-income':
            template_filename = "affidavit-of-no-income.docx"
        elif doc_type == 'joint_affidavit_two_disinterested_person': # New Template
            template_filename = "joint-affidavit-two-disenterested-person.docx"
            
        template_path = os.path.join(current_app.root_path, 'static', 'templates', template_filename)
        
        # 3. Prepare Context (The Mapping)
        # Party 1 (Primary Affiant)
        affiant = entry.parties[0]
        
        # Party 2 (Secondary Affiant for Joint Affidavits)
        affiant2_name = ""
        if len(entry.parties) > 1:
            affiant2_name = entry.parties[1].party_name.upper()

        # Date Logic (e.g., "8th", "January 2024")
        day_val = entry.not_date.strftime("%d")
        # Add ordinal suffix (st, nd, rd, th)
        if 4 <= int(day_val) <= 20 or 24 <= int(day_val) <= 30:
            suffix = "th"
        else:
            suffix = ["st", "nd", "rd"][int(day_val) % 10 - 1]
        day_str = f"{day_val}{suffix}"

        context = {
            # Party Details
            'Full_name': affiant.party_name.upper(),  # Matches {{ Full_name }}
            'Full_name1': affiant2_name,            # Matches {{ Full_name1 }} (2nd Party)
            'Citizenship': affiant.citizenship.title() if affiant.citizenship else 'Filipino',
            'Address': affiant.party_address,
            'Affiant': affiant.party_name.upper(),
            'ID_type': affiant.party_id_type,
            'ID_num': affiant.party_id_number,
            
            # Notarial Details
            'Doc_No': entry.not_entry_num,   # Ensure Word has {{ Doc_No }}
            'Page_No': entry.not_page_num,   # Ensure Word has {{ Page_No }}
            'Book_No': entry.not_book_num,   # Ensure Word has {{ Book_No }}
            'Series_of': entry.not_series,   # Ensure Word has {{ Series_of }}
        
            
            # Dates
            'day_of_month': day_str,  # Matches {{ day_of_month }}
            'month_year': entry.not_date.strftime("%B, %Y"), # Matches {{ month_year }}
        }

        # 4. Render
        doc = DocxTemplate(template_path)
        doc.render(context)
        
        # 5. Save & Send
        doc_ref = f"{entry.not_book_num}-{entry.not_page_num}-{entry.not_entry_num}-{entry.not_series}"
        temp_dir = tempfile.gettempdir()
        output_filename = f"{template_filename.rstrip('.docx')}-{doc_ref}.docx"
        output_path = os.path.join(temp_dir, output_filename)
        doc.save(output_path)
        
        return send_file(output_path, as_attachment=True)

    except Exception as e:
        flash(f"Error generating document: {str(e)}", "error")
        return redirect(request.referrer)


# app/routes/notarial_entries_routes.py

from sqlalchemy import func

@notarial_entries_bp.route('/api/parties/search', methods=['GET'])
@staff_or_admin_required
@login_required
def search_previous_parties_api():
    """
    Search for parties from previous notarial entries to auto-fill.
    """
    query = request.args.get('q', '').strip()
    
    # Don't search if less than 2 letters
    if not query or len(query) < 2:
        return jsonify([])
    
    try:
        # Search for parties matching the name (Case Insensitive)
        # Limit to 20 results to stay fast
        results = NotarialEntryParty.query.filter(
            NotarialEntryParty.party_name.ilike(f'%{query}%')
        ).order_by(NotarialEntryParty.id.desc()).limit(20).all()
        
        # Deduplicate (If Juan Cruz appears 10 times, show him once)
        unique_map = {}
        suggestions = []
        
        for p in results:
            # Use name as key to ensure uniqueness
            clean_name = p.party_name.strip()
            if clean_name.lower() not in unique_map:
                unique_map[clean_name.lower()] = True
                
                suggestions.append({
                    'party_name': clean_name,
                    'party_address': p.party_address,
                    'citizenship': p.citizenship,
                    'party_id_type': p.party_id_type,
                    'party_id_number': p.party_id_number,
                    'party_id_expiry': p.party_id_expiry.strftime('%Y-%m-%d') if p.party_id_expiry else ''
                })
        
        return jsonify(suggestions)
        
    except Exception as e:
        print(f"Error searching parties: {e}")
        return jsonify([])