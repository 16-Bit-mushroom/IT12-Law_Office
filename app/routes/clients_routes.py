from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_required

clients_bp = Blueprint('clients', __name__, url_prefix='/clients')

@clients_bp.route('/')
@login_required 

def clients_page():
    # For now, use empty list until we fix the service
    clients = []  # get_all_clients() - comment this out temporarily
    return render_template('clients_page.html', clients=clients)

@clients_bp.route('/new', methods=['GET'])
@login_required 

def new_client_form():
    return render_template('add_client.html')

@clients_bp.route('/new_submit', methods=['POST'])
@login_required 

def submit_new_client():
    # Temporarily comment out the service call
    # name = request.form['client_name']
    # email = request.form['client_email']
    # ctype = request.form['client_type']
    # status = request.form['client_status']
    # notes = request.form.get('internal_notes', '')
    # add_client(name, email, ctype, status, notes)
    
    return redirect(url_for('clients.clients_page'))