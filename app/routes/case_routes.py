# routes/case_routes.py
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime

from app.services.case_service import CaseService
from app.services.client_service import get_all_clients

case_bp = Blueprint('case', __name__, url_prefix='/cases')

@case_bp.route('/')
@login_required
def list_cases():
    """Display all cases"""
    cases = CaseService.get_all_cases()
    return render_template('cases/list.html', cases=cases)

@case_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_case():
    """Create a new case"""
    if request.method == 'GET':
        clients = get_all_clients()  # Get all clients for dropdown
        pre_select_client_id = request.args.get('pre_select_client_id', type=int)
        return render_template('cases/create.html', 
                             clients=clients,
                             pre_select_client_id=pre_select_client_id)
    
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
        
        # Prepare case data
        case_data = {
            'title': request.form.get('title'),
            'case_type': request.form.get('case_type'),
            'violation': request.form.get('violation'),
            'engagement_date': datetime.strptime(request.form.get('engagement_date'), '%Y-%m-%d').date(),
            'filing_date': datetime.strptime(request.form.get('filing_date'), '%Y-%m-%d').date() if request.form.get('filing_date') else None,
            'client_id': int(request.form.get('client_id')),
            'assigned_attorney_id': current_user.id,
            'status': 'active'
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
@login_required
def view_case(case_id):
    """View case details"""
    try:
        case = CaseService.get_case_by_id(case_id)
        if not case:
            flash('Case not found!', 'error')
            return redirect(url_for('case.list_cases'))
        
        # Get documents for this case
        from app.services.document_service import DocumentService
        documents = DocumentService.get_documents_by_parent('case', case_id)
        
        return render_template('cases/case_detail.html', 
                             case=case, 
                             documents=documents)
    except Exception as e:
        flash(f'Error loading case: {str(e)}', 'error')
        return redirect(url_for('case.list_cases'))

@case_bp.route('/<int:case_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_case(case_id):
    """Edit a case"""
    case = CaseService.get_case_by_id(case_id)
    if not case:
        flash('Case not found!', 'error')
        return redirect(url_for('case.list_cases'))
    
    if request.method == 'GET':
        clients = get_all_clients()
        return render_template('cases/edit_case.html', 
                             case=case, 
                             clients=clients)
    
    # Handle POST request
    try:
        # Validate required fields
        if not all([request.form.get('title'), 
                   request.form.get('engagement_date'), 
                   request.form.get('client_id')]):
            flash('Title, engagement date, and client are required!', 'error')
            clients = get_all_clients()
            return render_template('cases/edit_case.html', 
                                 case=case, 
                                 clients=clients)
        
        # Prepare case data
        case_data = {
            'title': request.form.get('title'),
            'case_type': request.form.get('case_type'),
            'violation': request.form.get('violation'),
            'engagement_date': datetime.strptime(request.form.get('engagement_date'), '%Y-%m-%d').date(),
            'filing_date': datetime.strptime(request.form.get('filing_date'), '%Y-%m-%d').date() if request.form.get('filing_date') else None,
            'client_id': int(request.form.get('client_id')),
            'assigned_attorney_id': current_user.id,
            'status': request.form.get('status', 'active')
        }
        
        # Update case
        updated_case = CaseService.update_case(case_id, case_data)
        flash(f'Case {updated_case.case_number} updated successfully!', 'success')
        return redirect(url_for('case.view_case', case_id=case_id))
        
    except Exception as e:
        flash(f'Error updating case: {str(e)}', 'error')
        clients = get_all_clients()
        return render_template('cases/edit_case.html', 
                             case=case, 
                             clients=clients)

@case_bp.route('/<int:case_id>/delete', methods=['POST'])
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