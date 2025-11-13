from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.services.transaction_service import (
    create_transaction, get_all_transactions, submit_for_approval, 
    approve_transaction, complete_transaction, mark_payment_paid
)
from app.services.client_service import get_all_clients
from app.services.service_service import get_all_services  # You'll need to create this

transaction_bp = Blueprint('transaction', __name__, url_prefix='/transactions')

@transaction_bp.route('/')
@login_required
def transactions_page():
    """Display all transactions"""
    transactions = get_all_transactions()
    return render_template('transactions_page.html', transactions=transactions)

@transaction_bp.route('/new', methods=['GET'])
@login_required
def new_transaction_form():
    """Display new transaction form with client and service selection"""
    clients = get_all_clients()
    services = get_all_services()  # You'll need to implement this
    pre_select_client_id = request.args.get('pre_select_client_id')
    
    return render_template('new_transaction_form.html', 
                         clients=clients, 
                         services=services,
                         pre_select_client_id=pre_select_client_id)

@transaction_bp.route('/new', methods=['POST'])
@login_required
def submit_new_transaction():
    """Create a new transaction"""
    try:
        transaction_data = {
            'client_id': request.form['client_id'],
            'service_id': request.form['service_id'],
            'amount': request.form['amount'],
            'document_title': request.form.get('document_title'),
            'document_purpose': request.form.get('document_purpose')
        }
        
        transaction = create_transaction(transaction_data)
        flash('Transaction created successfully! Status: Draft', 'success')
        return redirect(url_for('transaction.transactions_page'))
        
    except Exception as e:
        flash(f'Error creating transaction: {str(e)}', 'error')
        return redirect(url_for('transaction.new_transaction_form'))

@transaction_bp.route('/<int:transaction_id>/submit_approval', methods=['POST'])
@login_required
def submit_for_approval_route(transaction_id):
    """Submit transaction for lawyer approval"""
    try:
        transaction = submit_for_approval(transaction_id)
        flash('Transaction submitted for lawyer approval', 'success')
        return redirect(url_for('transaction.transactions_page'))
    except Exception as e:
        flash(f'Error submitting for approval: {str(e)}', 'error')
        return redirect(url_for('transaction.transactions_page'))

@transaction_bp.route('/<int:transaction_id>/approve', methods=['POST'])
@login_required
def approve_transaction_route(transaction_id):
    """Lawyer approves transaction"""
    if not current_user.is_admin:  # Or check for lawyer role
        flash('Only lawyers can approve transactions', 'error')
        return redirect(url_for('transaction.transactions_page'))
    
    try:
        lawyer_notes = request.form.get('lawyer_notes')
        transaction = approve_transaction(transaction_id, lawyer_notes)
        flash('Transaction approved! Document and notary entry created.', 'success')
        return redirect(url_for('transaction.transactions_page'))
    except Exception as e:
        flash(f'Error approving transaction: {str(e)}', 'error')
        return redirect(url_for('transaction.transactions_page'))

# Add similar routes for complete_transaction and mark_payment_paid