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
# Add this with your other imports
from app.services.system_log_service import SystemLogService
from app.models import db
from decimal import Decimal

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
    try:
        # 1. Inputs
        amount_str = request.form.get('payment_amount', '0')
        # Handle typo where amount might be empty
        if not amount_str: amount_str = '0'
        
        amount = Decimal(amount_str)
        method = request.form.get('payment_method')
        ref = request.form.get('payment_reference')
        note = request.form.get('payment_note')
        

        # 2. Add New Payment Record
        from app.models.payment_mdl import Payment
        from app.models.transaction_mdl import TransactionItem
        
        transaction = TransactionItem.query.get_or_404(transaction_id)
        if amount > transaction.balance:
            flash(f'Error: Payment of ₱{amount:,.2f} exceeds the balance of ₱{transaction.balance:,.2f}.', 'error')
            return redirect(request.referrer)
        
        new_payment = Payment(
            transaction_item_id=transaction.id,
            pay_amount=amount,
            pay_method=method,
            pay_ref=ref,
            notes=note
        )
        db.session.add(new_payment)
        
        # --- THE FIX ---
        # Flush sends the new payment to the DB transaction (but doesn't commit yet).
        # This ensures transaction.payments includes the new record for calculation.
        db.session.flush() 
        
        # Now we check the balance property directly. 
        # The 'balance' property in your model automatically subtracts all payments (including this new one).
        if transaction.balance <= 0:
            transaction.payment_status = 'Paid'
        else:
            transaction.payment_status = 'Partial'
            
        db.session.commit()
        
        # Log
        from app.services.system_log_service import SystemLogService
        SystemLogService.log('Payment', 'Finance', f"Received ₱{amount} ({method}) for {transaction.purpose}", transaction.id)
        
        flash(f'Payment of ₱{amount} recorded successfully!', 'success')
        
        # Smart Redirect
        if transaction.transaction_type == 'Case' and transaction.case_id:
             return redirect(url_for('case.view_case', case_id=transaction.case_id))
             
        return redirect(url_for('transaction.transactions_page'))

    except Exception as e:
        db.session.rollback()
        flash(f'Error recording payment: {str(e)}', 'error')
        return redirect(request.referrer or url_for('transaction.transactions_page'))

@transaction_bp.route('/<int:transaction_id>/update_amount', methods=['POST'])
@login_required
def update_transaction_amount(transaction_id):
    try:
        new_amount = Decimal(request.form.get('new_amount', 0))
        
        # Get Transaction
        from app.models.transaction_mdl import TransactionItem
        transaction = TransactionItem.query.get_or_404(transaction_id)
        
        # Security Check: Prevent making bill smaller than what's already paid
        if new_amount < transaction.total_paid:
            flash(f'Cannot reduce bill to {new_amount}. Client already paid {transaction.total_paid}.', 'error')
            return redirect(request.referrer)

        # Log Logic
        old_val = transaction.transaction_amount
        transaction.transaction_amount = new_amount
        
        # Auto-update status
        if transaction.total_paid >= new_amount:
            transaction.payment_status = 'Paid'
        else:
            transaction.payment_status = 'Partial' # or Pending if 0 paid

        db.session.commit()
        
        SystemLogService.log('Update', 'Finance', f"Adjusted bill from {old_val} to {new_amount}", transaction.id)
        flash('Bill amount updated successfully.', 'success')
        
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
        
    return redirect(request.referrer)

# app/routes/transaction_routes.py

# 1. GET HISTORY HTML (HTMX-style)
from flask import render_template  # Make sure to import this

@transaction_bp.route('/<int:transaction_id>/history', methods=['GET'])
@login_required
def get_transaction_history(transaction_id):
    # Ensure TransactionItem is imported at the top of the file
    from app.models.transaction_mdl import TransactionItem 
    
    transaction = TransactionItem.query.get_or_404(transaction_id)
    
    # ✅ SORTING FIX: Sort payments by pay_date descending (Latest First)
    sorted_payments = sorted(
        transaction.payments, 
        key=lambda p: p.pay_date, 
        reverse=True
    )
    
    # Pass the 'sorted_payments' list instead of the raw 'transaction.payments'
    return render_template('/transactions/_history_list.html', 
                           transaction=transaction, 
                           payments=sorted_payments)

# 2. VOID PAYMENT ROUTE
@transaction_bp.route('/payments/<int:payment_id>/void', methods=['POST'])
@login_required
def void_payment(payment_id):
    try:
        from app.models.payment_mdl import Payment
        from app.services.system_log_service import SystemLogService # Ensure import
        
        payment = Payment.query.get_or_404(payment_id)
        transaction = payment.transaction # Access parent relationship
        
        # Capture details for log
        amount = payment.pay_amount
        ref = payment.pay_ref
        trans_id = transaction.id
        case_id = transaction.case_id
        
        # DELETE
        db.session.delete(payment)
        
        # UPDATE PARENT STATUS
        # We need to calculate balance *after* deletion. 
        # Since flush/commit hasn't happened, we do it manually or commit first.
        db.session.commit() # Commit delete first
        
        # Now re-check balance
        # Force refresh of transaction relationship
        db.session.refresh(transaction)
        
        if transaction.balance <= 0:
            transaction.payment_status = 'Paid'
        else:
            transaction.payment_status = 'Pending' if transaction.total_paid == 0 else 'Partial'
            
        db.session.commit()
        
        SystemLogService.log('Delete', 'Finance', f"Voided payment of ₱{amount} ({ref})", trans_id)
        flash(f'Payment {ref} voided successfully.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error voiding payment: {str(e)}', 'error')
        
    return redirect(request.referrer)

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