# routes/case_routes.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime
from sqlalchemy import desc, asc, or_

from app.services.case_service import CaseService
from app.services.client_service import get_all_clients  # Only import get_all_clients
from app.services.suggestion_service import SuggestionService
from app.models.case_mdl import Case
from app.models.client_mdl import Client
from app.utils.permissions import admin_required


case_bp = Blueprint('case', __name__, url_prefix='/cases')

@case_bp.route('/')
@admin_required
@login_required
def list_cases():
    """Display all cases with filtering and sorting"""
    # Get filter parameters
    status_filter = request.args.get('status', 'all')
    sort_by = request.args.get('sort_by', 'created_at')
    sort_order = request.args.get('sort_order', 'desc')
    
    # Validate sort parameters
    valid_sort_columns = ['id', 'case_number', 'title', 'violation', 
                         'engagement_date', 'filing_date', 'status', 
                         'created_at', 'updated_at']
    
    if sort_by not in valid_sort_columns:
        sort_by = 'created_at'
    
    # Get cases with filtering and sorting
    cases_query = Case.query
    
    # Apply status filter
    if status_filter and status_filter != 'all':
        cases_query = cases_query.filter_by(status=status_filter)
    
    # Apply sorting
    if sort_order == 'asc':
        cases_query = cases_query.order_by(asc(getattr(Case, sort_by)))
    else:
        cases_query = cases_query.order_by(desc(getattr(Case, sort_by)))
    
    cases = cases_query.all()
    
    # Get counts for each status
    total_cases = Case.query.count()
    active_count = Case.query.filter_by(status='active').count()
    completed_count = Case.query.filter_by(status='completed').count()
    pending_count = Case.query.filter_by(status='pending').count()
    
    return render_template('cases/list.html', 
                         cases=cases,
                         total_cases=total_cases,
                         active_count=active_count,
                         completed_count=completed_count,
                         pending_count=pending_count,
                         current_status=status_filter,
                         sort_by=sort_by,
                         sort_order=sort_order)

@case_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_case():
    """Create a new case"""
    if request.method == 'GET':
        clients = get_all_clients()
        pre_select_client_id = request.args.get('pre_select_client_id', type=int)
        
        # Get initial suggestions
        case_type_suggestions = SuggestionService.get_case_suggestions('case_type')
        violation_suggestions = SuggestionService.get_case_suggestions('violation')
        cause_of_action_suggestions = SuggestionService.get_case_suggestions('cause_of_action')
        
        return render_template('cases/create.html', 
                             clients=clients,
                             pre_select_client_id=pre_select_client_id,
                             case_type_suggestions=case_type_suggestions,
                             violation_suggestions=violation_suggestions,
                             cause_of_action_suggestions=cause_of_action_suggestions)
    
    # Handle POST request
    try:
        # Validate required fields
        if not all([request.form.get('title'), 
                   request.form.get('engagement_date'), 
                   request.form.get('client_id')]):
            flash('Title, engagement date, and client are required!', 'error')
            clients = get_all_clients()
            pre_select_client_id = request.args.get('pre_select_client_id', type=int)
            return render_template('cases/create.html', 
                                 clients=clients,
                                 pre_select_client_id=pre_select_client_id)
        
        # Parse representatives data
        representatives = []
        rep_names = request.form.getlist('representative_name[]')
        rep_emails = request.form.getlist('representative_email[]')
        rep_phones = request.form.getlist('representative_phone[]')
        rep_roles = request.form.getlist('representative_role[]')
        
        for i in range(len(rep_names)):
            if rep_names[i].strip():  # Only add if name is not empty
                representatives.append({
                    'full_name': rep_names[i],
                    'email': rep_emails[i] if i < len(rep_emails) else '',
                    'phone': rep_phones[i] if i < len(rep_phones) else '',
                    'role': rep_roles[i] if i < len(rep_roles) else ''
                })
        
        # Get case type, violation, and cause of action
        case_type = request.form.get('case_type')
        violation = request.form.get('violation')
        cause_of_action = request.form.get('cause_of_action')
        
        # Record suggestions
        if case_type and case_type.strip():
            SuggestionService.add_suggestion('case', 'case_type', case_type.strip(), current_user.id)
        
        if violation and violation.strip():
            SuggestionService.add_suggestion('case', 'violation', violation.strip(), current_user.id)
        
        if cause_of_action and cause_of_action.strip():
            SuggestionService.add_suggestion('case', 'cause_of_action', cause_of_action.strip(), current_user.id)
        
        # Prepare case data - FIXED: Handle empty filing date properly
        engagement_date_str = request.form.get('engagement_date')
        filing_date_str = request.form.get('filing_date')
        
        engagement_date = datetime.strptime(engagement_date_str, '%Y-%m-%d').date() if engagement_date_str else None
        
        # Handle filing date - it's nullable
        filing_date = None
        if filing_date_str and filing_date_str.strip():  # Check if not empty
            try:
                filing_date = datetime.strptime(filing_date_str, '%Y-%m-%d').date()
            except ValueError:
                # If date format is invalid, leave as None
                filing_date = None
        
        case_data = {
            'title': request.form.get('title'),
            'case_category': request.form.get('case_category', 'individual'),
            'case_type': case_type,
            'violation': violation,
            'cause_of_action': cause_of_action,
            'engagement_date': engagement_date,
            'filing_date': filing_date,  # This can be None
            'client_id': int(request.form.get('client_id')),
            'assigned_attorney_id': current_user.id,
            'status': 'active',
            'representatives': representatives
        }
        
        # Create case
        new_case = CaseService.create_case(case_data)
        flash(f'Case {new_case.case_number} created successfully!', 'success')
        return redirect(url_for('case.list_cases'))
        
    except Exception as e:
        flash(f'Error creating case: {str(e)}', 'error')
        clients = get_all_clients()
        pre_select_client_id = request.args.get('pre_select_client_id', type=int)
        return render_template('cases/create.html', 
                             clients=clients,
                             pre_select_client_id=pre_select_client_id)

@case_bp.route('/<int:case_id>')
@admin_required
@login_required
def view_case(case_id):
    """View case details"""
    try:
        case = CaseService.get_case_by_id(case_id)
        if not case:
            flash('Case not found!', 'error')
            return redirect(url_for('case.list_cases'))
        
        # Get representatives for this case
        representatives = CaseService.get_case_representatives(case_id)
        
        # Get documents for this case
        from app.services.document_service import DocumentService
        documents = DocumentService.get_documents_by_parent('case', case_id)
        
        return render_template('cases/case_detail.html', 
                             case=case, 
                             representatives=representatives,
                             documents=documents)
    except Exception as e:
        flash(f'Error loading case: {str(e)}', 'error')
        return redirect(url_for('case.list_cases'))

@case_bp.route('/<int:case_id>/edit', methods=['GET', 'POST'])
@admin_required
@login_required
def edit_case(case_id):
    """Edit a case"""
    case = CaseService.get_case_by_id(case_id)
    if not case:
        flash('Case not found!', 'error')
        return redirect(url_for('case.list_cases'))
    
    if request.method == 'GET':
        clients = get_all_clients()
        representatives = CaseService.get_case_representatives(case_id)
        
        # Get suggestions for editing
        case_type_suggestions = SuggestionService.get_case_suggestions('case_type')
        violation_suggestions = SuggestionService.get_case_suggestions('violation')
        cause_of_action_suggestions = SuggestionService.get_case_suggestions('cause_of_action')
        
        return render_template('cases/edit_case.html', 
                             case=case, 
                             clients=clients,
                             representatives=representatives,
                             case_type_suggestions=case_type_suggestions,
                             violation_suggestions=violation_suggestions,
                             cause_of_action_suggestions=cause_of_action_suggestions)
    
    # Handle POST request
    try:
        # Validate required fields
        if not all([request.form.get('title'), 
                   request.form.get('engagement_date'), 
                   request.form.get('client_id')]):
            flash('Title, engagement date, and client are required!', 'error')
            clients = get_all_clients()
            representatives = CaseService.get_case_representatives(case_id)
            return render_template('cases/edit_case.html', 
                                 case=case, 
                                 clients=clients,
                                 representatives=representatives)
        
        # Parse representatives data
        representatives = []
        rep_names = request.form.getlist('representative_name[]')
        rep_emails = request.form.getlist('representative_email[]')
        rep_phones = request.form.getlist('representative_phone[]')
        rep_roles = request.form.getlist('representative_role[]')
        
        for i in range(len(rep_names)):
            if rep_names[i].strip():  # Only add if name is not empty
                representatives.append({
                    'full_name': rep_names[i],
                    'email': rep_emails[i] if i < len(rep_emails) else '',
                    'phone': rep_phones[i] if i < len(rep_phones) else '',
                    'role': rep_roles[i] if i < len(rep_roles) else ''
                })
        
        # Get case type, violation, and cause of action
        case_type = request.form.get('case_type')
        violation = request.form.get('violation')
        cause_of_action = request.form.get('cause_of_action')
        
        # Record suggestions
        if case_type and case_type.strip():
            SuggestionService.add_suggestion('case', 'case_type', case_type.strip(), current_user.id)
        
        if violation and violation.strip():
            SuggestionService.add_suggestion('case', 'violation', violation.strip(), current_user.id)
        
        if cause_of_action and cause_of_action.strip():
            SuggestionService.add_suggestion('case', 'cause_of_action', cause_of_action.strip(), current_user.id)
        
        # Prepare case data - FIXED: Handle empty filing date properly
        engagement_date_str = request.form.get('engagement_date')
        filing_date_str = request.form.get('filing_date')
        
        engagement_date = datetime.strptime(engagement_date_str, '%Y-%m-%d').date() if engagement_date_str else None
        
        # Handle filing date - it's nullable
        filing_date = None
        if filing_date_str and filing_date_str.strip():  # Check if not empty
            try:
                filing_date = datetime.strptime(filing_date_str, '%Y-%m-%d').date()
            except ValueError:
                # If date format is invalid, leave as None
                filing_date = None
        
        case_data = {
            'title': request.form.get('title'),
            'case_category': request.form.get('case_category', 'individual'),
            'case_type': case_type,
            'violation': violation,
            'cause_of_action': cause_of_action,
            'engagement_date': engagement_date,
            'filing_date': filing_date,  # This can be None
            'client_id': int(request.form.get('client_id')),
            'assigned_attorney_id': current_user.id,
            'status': request.form.get('status', 'active'),
            'representatives': representatives
        }
        
        # Update case
        updated_case = CaseService.update_case(case_id, case_data)
        flash(f'Case {updated_case.case_number} updated successfully!', 'success')
        return redirect(url_for('case.view_case', case_id=case_id))
        
    except Exception as e:
        flash(f'Error updating case: {str(e)}', 'error')
        clients = get_all_clients()
        representatives = CaseService.get_case_representatives(case_id)
        return render_template('cases/edit_case.html', 
                             case=case, 
                             clients=clients,
                             representatives=representatives)

@case_bp.route('/<int:case_id>/delete', methods=['POST'])
@admin_required
@login_required
def delete_case(case_id):
    """Delete a case"""
    try:
        case_number = CaseService.delete_case(case_id)
        flash(f'Case {case_number} has been deleted successfully!', 'success')
        
    except ValueError as e:
        flash(str(e), 'error')
    except Exception as e:
        print(f"ERROR deleting case: {e}")
        flash(f'Error deleting case: {str(e)}', 'error')
    
    return redirect(url_for('case.list_cases'))

# ===== NEW API ENDPOINTS FOR AUTO-SUGGESTIONS =====

@case_bp.route('/api/clients/search')
@login_required
def search_clients_api():
    """Search clients for auto-suggest"""
    query = request.args.get('q', '')
    limit = request.args.get('limit', 10, type=int)
    
    if not query or len(query) < 2:
        return jsonify([])
    
    # Search clients by name or email
    clients = Client.query.filter(
        (Client.client_first_name.ilike(f'%{query}%')) |
        (Client.client_last_name.ilike(f'%{query}%')) |
        (Client.client_email.ilike(f'%{query}%')) |
        (Client.client_phone.ilike(f'%{query}%'))
    ).limit(limit).all()
    
    result = [{
        'id': client.id,
        'full_name': f"{client.client_first_name} {client.client_last_name}",
        'email': client.client_email,
        'phone': client.client_phone
    } for client in clients]
    
    return jsonify(result)

@case_bp.route('/api/cases/suggestions/<field>')
@login_required
def get_suggestions_api(field):
    """Get suggestions for a specific field"""
    valid_fields = ['case_type', 'violation', 'cause_of_action']
    
    if field not in valid_fields:
        return jsonify({'error': 'Invalid field'}), 400
    
    suggestions = SuggestionService.get_case_suggestions(field)
    
    # Format for frontend
    result = [{'value': suggestion} for suggestion in suggestions]
    
    return jsonify(result)

@case_bp.route('/api/cases/suggestions/<field>/search')
@login_required
def search_suggestions_api(field):
    """Search suggestions for a specific field"""
    valid_fields = ['case_type', 'violation', 'cause_of_action']
    
    if field not in valid_fields:
        return jsonify({'error': 'Invalid field'}), 400
    
    query = request.args.get('q', '')
    limit = request.args.get('limit', 10, type=int)
    
    if not query:
        return jsonify([])
    
    # Search suggestions from the database
    from app.models.suggestion_mdl import Suggestion
    
    suggestions = Suggestion.query.filter_by(
        module='case',
        suggestion_type=field,
        is_active=True
    ).filter(
        Suggestion.value.ilike(f'%{query}%')
    ).order_by(
        Suggestion.use_count.desc()
    ).limit(limit).all()
    
    result = [{
        'value': suggestion.value,
        'use_count': suggestion.use_count,
        'last_used': suggestion.last_used.isoformat() if suggestion.last_used else None
    } for suggestion in suggestions]
    
    return jsonify(result)

@case_bp.route('/api/cases/suggestions/<field>/remove', methods=['POST'])
@login_required
def remove_suggestion_api(field):
    """Remove a suggestion (soft delete)"""
    valid_fields = ['case_type', 'violation', 'cause_of_action']
    
    if field not in valid_fields:
        return jsonify({'error': 'Invalid field'}), 400
    
    data = request.get_json()
    value = data.get('value')
    
    if not value:
        return jsonify({'error': 'Value is required'}), 400
    
    # Soft delete the suggestion
    success = SuggestionService.remove_suggestion('case', field, value)
    
    if success:
        return jsonify({'success': True, 'message': 'Suggestion removed'})
    else:
        return jsonify({'error': 'Suggestion not found'}), 404

# ===== CASE TYPE MANAGEMENT =====

@case_bp.route('/api/case-types')
@login_required
def get_case_types_api():
    """Get all case type suggestions"""
    suggestions = SuggestionService.get_case_suggestions('case_type', limit=50)
    
    # Include some default case types
    default_types = ['Civil', 'Criminal', 'Corporate', 'Family Law', 
                    'Property', 'Labor', 'Administrative', 'Other']
    
    # Combine and deduplicate
    all_types = list(set(default_types + suggestions))
    all_types.sort()
    
    return jsonify(all_types)