from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.models.service_mdl import Service
from app.services.transaction_service import (
    get_all_transactions, submit_for_approval, 
    approve_transaction, complete_transaction, mark_payment_paid
)
from app.services.client_service import get_all_clients

transaction_bp = Blueprint('transaction', __name__, url_prefix='/transactions')

@transaction_bp.route('/')
@login_required
def transactions_page():
    """Display all transactions (auto-created from notarial entries and cases)"""
    transactions = get_all_transactions()
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