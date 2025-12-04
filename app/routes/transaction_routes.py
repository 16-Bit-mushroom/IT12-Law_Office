from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.models.service_mdl import Service
from app.services.transaction_service import (
    get_all_transactions, submit_for_approval, 
    approve_transaction, complete_transaction, mark_payment_paid
)
from app.services.client_service import get_all_clients
# Add this import at the top of your transaction routes file
from app.models.notarial_entry_mdl import NotarialEntry
from app.models.transaction_mdl import TransactionItem
from app.models.case_logs_mdl import CaseDocument  # Assuming you have this model
from app.utils.permissions import staff_or_admin_required
from app.utils.query_filters import get_accessible_transactions

transaction_bp = Blueprint('transaction', __name__, url_prefix='/transactions')

@transaction_bp.route('/')
@staff_or_admin_required
@login_required
def transactions_page():
    """Display all transactions (auto-created from notarial entries and cases)"""
    # Get all transactions
    transactions = get_all_transactions()
    
    # ROLE-BASED FILTERING: Staff cannot see case transactions
    if current_user.role == 'staff':
        transactions = [t for t in transactions if t.transaction_type != 'Case']
    
    return render_template('transactions_page.html', transactions=transactions)

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
    if not current_user.is_admin:
        flash('Only authorized users can approve transactions', 'error')
        return redirect(url_for('transaction.transactions_page'))
    
    try:
        transaction = approve_transaction(transaction_id)
        flash('Transaction approved successfully!', 'success')
        return redirect(url_for('transaction.transactions_page'))
    except Exception as e:
        flash(f'Error approving transaction: {str(e)}', 'error')
        return redirect(url_for('transaction.transactions_page'))

@transaction_bp.route('/<int:transaction_id>/mark_paid', methods=['POST'])
@login_required
def mark_payment_paid_route(transaction_id):
    """Mark transaction as paid"""
    try:
        payment_method = request.form['payment_method']
        payment_reference = request.form.get('payment_reference', '')
        
        transaction = mark_payment_paid(transaction_id, payment_method, payment_reference)
        flash('Payment marked as paid!', 'success')
        return redirect(url_for('transaction.transactions_page'))
    except Exception as e:
        flash(f'Error updating payment: {str(e)}', 'error')
        return redirect(url_for('transaction.transactions_page'))

@transaction_bp.route('/<int:transaction_id>/complete', methods=['POST'])
@login_required
def complete_transaction_route(transaction_id):
    """Mark transaction as completed"""
    try:
        transaction = complete_transaction(transaction_id)
        flash('Transaction completed!', 'success')
        return redirect(url_for('transaction.transactions_page'))
    except Exception as e:
        flash(f'Error completing transaction: {str(e)}', 'error')
        return redirect(url_for('transaction.transactions_page'))

@transaction_bp.route('/<int:transaction_id>/view')
@login_required
def view_transaction_details(transaction_id):
    """Redirect to the appropriate detail page based on transaction type"""
    transaction = TransactionItem.query.get_or_404(transaction_id)
    
    if transaction.transaction_type == 'Notarial':
        # Get the notarial entry linked to this transaction
        notarial_entry = NotarialEntry.query.filter_by(
            transaction_item_id=transaction.id
        ).first()
        
        if notarial_entry:
            # FIXED: Use the correct endpoint name
            return redirect(url_for('notarial_entries.entry_details', 
                                   entry_id=notarial_entry.id))
        else:
            flash('No notarial entry found for this transaction', 'error')
            return redirect(url_for('transaction.transactions_page'))
    
    elif transaction.transaction_type == 'Case':
        # Check if transaction has a direct case_id link
        if transaction.case_id:
            return redirect(url_for('case.view_case', 
                                   case_id=transaction.case_id))
        else:
            flash('No case found for this transaction', 'error')
            return redirect(url_for('transaction.transactions_page'))
    
    else:
        flash('Unknown transaction type', 'error')
        return redirect(url_for('transaction.transactions_page'))