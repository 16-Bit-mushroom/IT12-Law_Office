from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from app.services.client_service import add_client, get_all_clients, get_client_by_email

clients_bp = Blueprint('clients', __name__, url_prefix='/clients')

@clients_bp.route('/')
@login_required 
def clients_page():
    clients = get_all_clients()
    return render_template('clients_page.html', clients=clients)

@clients_bp.route('/new', methods=['GET'])
@login_required 
def new_client_form():
    """Displays the form to add a new client."""
    return render_template('add_client.html')

@clients_bp.route('/new', methods=['POST'])
@login_required 
def submit_new_client():
    """Submits new client data."""
    # Get form data including names
    first_name = request.form['client_first_name']
    last_name = request.form['client_last_name']
    address = request.form['client_address']
    email = request.form['client_email']
    phone = request.form.get('client_phone')
    role = request.form.get('client_role')
    notes = request.form.get('internal_notes', '')

    # Validation: Check for duplicate email
    if get_client_by_email(email):
        flash('A client with this email already exists.', 'error')
        return redirect(url_for('clients.new_client_form'))

    try:
        new_client = add_client(address, email, phone, role, notes, first_name, last_name)
        flash(f'Client {first_name} {last_name} added successfully.', 'success')
        

        return redirect(url_for('case_logs.new_case_form', pre_select_client_id=new_client.id))

        
    except Exception as e:
        flash(f'An error occurred while adding the client: {e}', 'error')
        # Ensure we keep the return_to parameter if there is an error so they don't lose their place
        return_to = request.args.get('return_to', '')
        return redirect(url_for('clients.new_client_form', return_to=return_to))