# routes/case_routes.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timezone, timedelta
from sqlalchemy import desc, asc, or_


from app.services.case_service import CaseService
from app.services.client_service import get_all_clients  # Only import get_all_clients
from app.services.suggestion_service import SuggestionService
from app.models.service_mdl import Service

from app.models.case_mdl import Case
from app.models.client_mdl import Client
from app.utils.permissions import admin_required
from app.services.schedule_service import ScheduleService # New import
from app.models.schedule_mdl import Schedule # New import if needed directly
from app.services.system_log_service import SystemLogService
from app.models.transaction_mdl import TransactionItem # Ensure this is imported
from app.services.transaction_service import mark_payment_paid
from app.models import db


case_bp = Blueprint('case', __name__, url_prefix='/cases')
PHT = timezone(timedelta(hours=8))

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
        
        # 1. Get the ID from URL
        client_id_arg = request.args.get('pre_select_client_id', type=int)
        pre_selected_client = None
        
        # 2. FIX: Actually fetch the client object!
        if client_id_arg:
            pre_selected_client = Client.query.get(client_id_arg)
        
        # Get initial suggestions
        case_type_suggestions = SuggestionService.get_case_suggestions('case_type')
        violation_suggestions = SuggestionService.get_case_suggestions('violation')
        cause_of_action_suggestions = SuggestionService.get_case_suggestions('cause_of_action')
        
        return render_template('cases/create.html', 
                             clients=clients,
                             # 3. Pass the OBJECT, not just the ID
                             pre_selected_client=pre_selected_client,
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
            
        try:
            acceptance_fee = float(request.form.get('acceptance_fee', 0))
        except ValueError:
            acceptance_fee = 0.0
        
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

        try:
            total_fee = float(request.form.get('acceptance_fee', 0))
            initial_pay = float(request.form.get('initial_payment', 0))
        except:
            total_fee = 0
            initial_pay = 0
            
        pay_method = request.form.get('pay_method')
        pay_ref = request.form.get('pay_ref')
                
        
        
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
            'representatives': representatives,
            'acceptance_fee': acceptance_fee,
            'initial_payment': initial_pay,
            'pay_method': pay_method,
            'pay_ref': pay_ref,
            
        }
        
        # Create case
        new_case = CaseService.create_case(case_data)
        
        # --- LOGGING ---
        SystemLogService.log('Create', 'Case', f"Opened new case: {new_case.title}", new_case.id)
        # ---------------
        
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

        # --- NEW: Get Schedules ---
        schedules = ScheduleService.get_schedules_by_case(case_id)
        
        # Pass datetime.now() for the template to calculate "Overdue" logic
        now = datetime.now(PHT).date()
        
        # --- NEW: Get Primary Transaction for Payment Status ---
        transaction = TransactionItem.query.filter_by(case_id=case_id).order_by(TransactionItem.id.asc()).first()
        
        return render_template('cases/case_detail.html', 
                             case=case, 
                             representatives=representatives,
                             documents=documents,
                             schedules=schedules,
                             transaction=transaction, # Pass transaction to template
                             now=now)
        
        return render_template('cases/case_detail.html', 
                             case=case, 
                             representatives=representatives,
                             documents=documents,
                             schedules=schedules,  # <--- Pass this
                             now=now)             # <--- Pass this
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
        
        old_data = {
            'title': case.title,
            'status': case.status,
            'violation': case.violation,
            'type': case.case_type
        }
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
            'case_type': request.form.get('case_type'),
            'violation': request.form.get('violation'),
            'cause_of_action': request.form.get('cause_of_action'),
            'engagement_date': engagement_date, # From your existing parsing
            'filing_date': filing_date,         # From your existing parsing
            'client_id': int(request.form.get('client_id')),
            'assigned_attorney_id': current_user.id,
            'status': request.form.get('status', 'active'),
            'representatives': representatives
        }
        
        # Update case
        updated_case = CaseService.update_case(
            case_id, 
            case_data, 
            user_role=current_user.role # Pass the role for locking logic
        )   
        
        new_data = {
            'title': updated_case.title,
            'status': updated_case.status,
            'violation': updated_case.violation,
            'type': updated_case.case_type
        }
        
        # --- LOGGING (Only if changed) ---
        if old_data != new_data:
            SystemLogService.log(
                action='Update',
                module='Case',
                description=f"Updated details for Case #{case.case_number}",
                entity_id=case.id,
                old_val=old_data,
                new_val=new_data
            )
        # ---------------------------------
        
        flash(f'Case {updated_case.case_number} updated successfully!', 'success')
        return redirect(url_for('case.view_case', case_id=case_id))
    
    except PermissionError as e:
        # Handle the Lock Error specifically
        flash(str(e), 'error')
        return redirect(url_for('case.view_case', case_id=case_id))
    
    except ValueError as e:
        # Logic Validation (No Filing Date / Lacking Docs)
        flash(f'Validation Error: {str(e)}', 'warning') # Use warning for logic issues
        return redirect(url_for('case.view_case', case_id=case_id))
        
    except Exception as e:
        # MERGED ERROR HANDLER: Logs error and re-renders form so user doesn't lose data
        print(f"Error updating case: {e}") # Print to console for debugging
        flash(f'Error updating case: {str(e)}', 'error')

@case_bp.route('/<int:case_id>/delete', methods=['POST'])
@admin_required
@login_required
def delete_case(case_id):
    """Delete a case"""
    try:
        case_number = CaseService.delete_case(case_id)
        
        SystemLogService.log(
            action='Delete', 
            module='Case', 
            description=f"Moved Case {case_number} to Recycle Bin", 
            entity_id=case_id
        )
        
        flash(f'Case {case_number} has been deleted successfully!', 'success')
        
    except ValueError as e:
        flash(str(e), 'error')
    except Exception as e:
        print(f"ERROR deleting case: {e}")
        flash(f'Error deleting case: {str(e)}', 'error')
    
    return redirect(url_for('case.list_cases'))

# ===== NEW API ENDPOINTS FOR AUTO-SUGGESTIONS =====

# app/routes/case_routes.py

@case_bp.route('/api/clients/search')
@login_required
def search_clients_api():
    """Search clients (Fixed for New Schema)"""
    query = request.args.get('q', '')
    limit = request.args.get('limit', 10, type=int)
    
    if not query or len(query) < 2:
        return jsonify([])
    
    # FIX: Use new column names (first_name, email, company_name)
    clients = Client.query.filter(
        or_(
            Client.first_name.ilike(f'%{query}%'),
            Client.last_name.ilike(f'%{query}%'),
            Client.company_name.ilike(f'%{query}%'),
            Client.email.ilike(f'%{query}%')
        )
    ).filter(Client.deleted_at == None).limit(limit).all()
    
    result = [{
        'id': client.id,
        'full_name': client.full_name, # Uses the smart property
        'email': client.email,
        'phone': client.phone or ''
    } for client in clients]
    
    return jsonify(result)

# app/routes/case_routes.py

# ... (Previous code) ...

# ===== NEW API ENDPOINTS FOR AUTO-SUGGESTIONS =====

# ... (search_clients_api remains the same) ...

@case_bp.route('/api/cases/suggestions/<field>')
@login_required
def get_suggestions_api(field):
    """Get suggestions for a specific field"""
    # UPDATE THIS LIST
    valid_fields = ['case_type', 'violation', 'cause_of_action', 'document_type']
    
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
    # UPDATE THIS LIST
    valid_fields = ['case_type', 'violation', 'cause_of_action', 'document_type']
    
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
    # UPDATE THIS LIST
    valid_fields = ['case_type', 'violation', 'cause_of_action', 'document_type']
    
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

# 1. Route to SHOW the separate 'Add Schedule' page (GET)
@case_bp.route('/<int:case_id>/schedule/new', methods=['GET'])
@login_required
def add_schedule_page(case_id):
    """Render the page to add a new schedule"""
    case = CaseService.get_case_by_id(case_id)
    if not case:
        flash('Case not found', 'error')
        return redirect(url_for('case.list_cases'))
        
    return render_template('schedules/add_schedule.html', case=case)

# 2. Route to SAVE the schedule (POST)
@case_bp.route('/<int:case_id>/schedule/add', methods=['POST'])
@login_required
def add_schedule_submission(case_id):
    """Handle the form submission"""
    try:
        title = request.form.get('title')
        details = request.form.get('details') # <-- Add this
        deadline_str = request.form.get('deadline')
        priority = request.form.get('priority', 'normal')

        if not title or not deadline_str:
            flash('Title and Deadline are required', 'error')
            # Redirect back to the add page on error
            return redirect(url_for('case.add_schedule_page', case_id=case_id))

        deadline = datetime.strptime(deadline_str, '%Y-%m-%d').date()

        schedule_data = {
            'title': title,
            'details': details,
            'deadline': deadline,
            'priority': priority,
            'case_id': case_id
        }

        ScheduleService.create_schedule(schedule_data)
        flash('Schedule added successfully', 'success')
        
    except Exception as e:
        flash(f'Error adding schedule: {str(e)}', 'error')
        return redirect(url_for('case.add_schedule_page', case_id=case_id))
    
    # On success, go back to the Case Detail view
    return redirect(url_for('case.view_case', case_id=case_id))

# 3. Route to TOGGLE status
@case_bp.route('/schedule/<int:schedule_id>/toggle', methods=['POST'])
@login_required
def toggle_schedule(schedule_id):
    try:
        schedule = ScheduleService.toggle_status(schedule_id)
        if schedule:
            return redirect(url_for('case.view_case', case_id=schedule.case_id))
        else:
            flash('Schedule not found', 'error')
            return redirect(url_for('case.list_cases'))
    except Exception as e:
        flash(f'Error updating schedule: {str(e)}', 'error')
        return redirect(url_for('case.list_cases'))
    

# app/routes/case_routes.py
# ... keep existing imports ...

# 1. EDIT PAGE (GET)
@case_bp.route('/<int:case_id>/schedule/<int:schedule_id>/edit', methods=['GET'])
@login_required
def edit_schedule_page(case_id, schedule_id):
    case = CaseService.get_case_by_id(case_id)
    schedule = ScheduleService.get_schedule_by_id(schedule_id)
    
    if not case or not schedule or schedule.case_id != case_id:
        flash('Schedule or Case not found', 'error')
        return redirect(url_for('case.list_cases'))
        
    return render_template('schedules/edit_schedule.html', case=case, schedule=schedule)

# 2. UPDATE ACTION (POST)
@case_bp.route('/<int:case_id>/schedule/<int:schedule_id>/update', methods=['POST'])
@login_required
def edit_schedule_submission(case_id, schedule_id):
    try:
        title = request.form.get('title')
        details = request.form.get('details')
        deadline_str = request.form.get('deadline')
        priority = request.form.get('priority')
        change_reason = request.form.get('change_reason')

        if not title or not deadline_str:
            flash('Title and Deadline are required', 'error')
            return redirect(url_for('case.edit_schedule_page', case_id=case_id, schedule_id=schedule_id))

        deadline = datetime.strptime(deadline_str, '%Y-%m-%d').date()

        data = {
            'title': title,
            'details': details,
            'deadline': deadline,
            'priority': priority,
            'change_reason': change_reason # Pass to service
        }

        ScheduleService.update_schedule(schedule_id, data)
        flash('Schedule updated successfully', 'success')
        
    except Exception as e:
        flash(f'Error updating schedule: {str(e)}', 'error')
        return redirect(url_for('case.edit_schedule_page', case_id=case_id, schedule_id=schedule_id))
    
    return redirect(url_for('case.view_case', case_id=case_id))

# 3. DELETE ACTION (POST)
@case_bp.route('/schedule/<int:schedule_id>/delete', methods=['POST'])
@login_required
def delete_schedule(schedule_id):
    try:
        # Get schedule first to know which case to return to
        schedule = ScheduleService.get_schedule_by_id(schedule_id)
        if not schedule:
            flash('Schedule not found', 'error')
            return redirect(url_for('case.list_cases'))
            
        case_id = schedule.case_id
        ScheduleService.delete_schedule(schedule_id)
        flash('Task deleted successfully', 'success')
        return redirect(url_for('case.view_case', case_id=case_id))
        
    except Exception as e:
        flash(f'Error deleting schedule: {str(e)}', 'error')
        return redirect(url_for('case.list_cases'))


@case_bp.route('/<int:case_id>/mark-paid', methods=['POST'])
@login_required
def mark_case_paid(case_id):
    """Mark the case transaction as paid (Simplified)"""
    try:
        # Find the transaction
        transaction = TransactionItem.query.filter_by(case_id=case_id).order_by(TransactionItem.id.asc()).first()
        
        if not transaction:
            flash('No transaction found for this case.', 'error')
            return redirect(url_for('case.view_case', case_id=case_id))
            
        # UPDATED: No longer reading from request.form
        # We pass "Manual" as the method and empty string for OR since they are removed from UI
        mark_payment_paid(transaction.id, payment_method="Manual", payment_reference="")
        
        # Log it
        SystemLogService.log('Payment', 'Case', f"Case #{case.case_number} marked as Paid", case_id)
        
        flash('Case marked as Paid successfully!', 'success')
        return redirect(url_for('case.view_case', case_id=case_id))
        
    except Exception as e:
        flash(f'Error updating payment: {str(e)}', 'error')
        return redirect(url_for('case.view_case', case_id=case_id))
    
# app/routes/case_routes.py

@case_bp.route('/<int:case_id>/add_fee', methods=['POST'])
@login_required
def add_case_fee(case_id):
    """Add a new billable item (Appearance Fee, etc.) to a case"""
    try:
        case = Case.query.get_or_404(case_id)
        
        purpose = request.form.get('purpose')
        amount = float(request.form.get('amount', 0))
        fee_type = request.form.get('fee_type')
        
        # Validation
        if not purpose or amount <= 0:
            flash('Invalid details. Purpose and positive amount required.', 'error')
            return redirect(url_for('case.view_case', case_id=case_id))

        # Create Transaction
        # We need to get a default service ID for 'Legal Fees' or similar
        # For now, we reuse the first service found or a specific 'Appearance Fee' service if you have one
        service = Service.query.filter_by(is_notarization=False).first()
        
        transaction = TransactionItem(
            client_id=case.client_id,
            service_id=service.id,
            case_id=case.id,
            transaction_type='Case',
            purpose=f"{fee_type}: {purpose}", # e.g., "Appearance Fee: Hearing Oct 12"
            transaction_amount=amount,
            payment_status='Pending'
        )
        
        db.session.add(transaction)
        db.session.commit()
        
        SystemLogService.log('Create', 'Finance', f"Added bill: {purpose} (₱{amount}) to Case #{case.case_number}", case.id)
        flash('New fee added successfully.', 'success')
        
        return redirect(url_for('case.view_case', case_id=case_id))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error adding fee: {str(e)}', 'error')
        return redirect(url_for('case.view_case', case_id=case_id))

@case_bp.route('/<int:case_id>/undo-payment', methods=['POST'])
@login_required
def undo_case_payment(case_id):
    """Revert case payment status to Pending"""
    try:
        # Find the transaction
        transaction = TransactionItem.query.filter_by(case_id=case_id).order_by(TransactionItem.id.asc()).first()
        
        if not transaction:
            flash('No transaction found for this case.', 'error')
            return redirect(url_for('case.view_case', case_id=case_id))
            
        # 1. Reset Transaction
        transaction.payment_status = 'Pending'
        transaction.payment_date = None
        
        # 2. Reset Linked Payment Record (ONLY if it exists)
        # This check prevents the "NoneType" error
        if transaction.payment:
            transaction.payment.payment_status = 'Pending'
            transaction.payment.pay_date = None
            transaction.payment.pay_method = None
            transaction.payment.pay_ref = None
            
        db.session.commit()
        
        # Log it
        case = Case.query.get(case_id)
        SystemLogService.log('Update', 'Case', f"Reverted payment status for Case #{case.case_number}", case_id)
        
        flash('Payment status reverted to Unpaid.', 'info')
        return redirect(url_for('case.view_case', case_id=case_id))
        
    except Exception as e:
        db.session.rollback()
        # Print error to console for debugging
        print(f"Error undoing payment: {e}") 
        flash(f'Error undoing payment: {str(e)}', 'error')
        return redirect(url_for('case.view_case', case_id=case_id))