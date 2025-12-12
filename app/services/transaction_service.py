from app.models import db
from app.models.transaction_mdl import TransactionItem
from app.models.payment_mdl import Payment
from app.models.case_logs_mdl import CaseDocument
from app.models.notarial_entry_mdl import NotarialEntry
from app.models.service_mdl import Service
# Add this import at the top of transaction_service.py
from app.models.case_mdl import Case
import uuid
from datetime import datetime, timezone, timedelta

PHT = timezone(timedelta(hours=8))


def create_transaction_from_notarial_entry(notarial_entry, client_id, service_id):
    """Automatically create transaction when notarial entry is created"""
    try:
        transaction = TransactionItem(
            client_id=client_id,
            service_id=service_id,
            transaction_type='Notarial',
            purpose=notarial_entry.not_title,
            transaction_amount=notarial_entry.not_fee,
            payment_status='Pending'
        )
        db.session.add(transaction)
        db.session.commit()
        
        # Auto-create pending payment
        create_pending_payment(transaction)
        
        # Link notarial entry to transaction
        notarial_entry.transaction_item_id = transaction.id
        db.session.commit()
        
        return transaction
    except Exception as e:
        db.session.rollback()
        raise e

def create_transaction_from_case(case, client_id, service_id, purpose, amount):
    """Automatically create transaction when case service is performed"""
    try:
        transaction = TransactionItem(
            client_id=client_id,
            service_id=service_id,
            transaction_type='Case',
            purpose=purpose,
            transaction_amount=amount,
            payment_status='Pending',
            case_id=case.id
        )
        db.session.add(transaction)
        db.session.commit()
        
        # Auto-create pending payment
        create_pending_payment(transaction)
        
        return transaction
    except Exception as e:
        db.session.rollback()
        raise e

# Remove the duplicate create_pending_payment function
# Keep only one version

def create_pending_payment(transaction):
    """Auto-create a pending payment record"""
    try:
        payment = Payment(
            pay_method='Pending',
            pay_ref=f"INV-{transaction.id}-{uuid.uuid4().hex[:8].upper()}",
            pay_type=transaction.transaction_type,
            pay_amount=transaction.transaction_amount,
            payment_status='Pending'
        )
        db.session.add(payment)
        db.session.flush()
        
        # Link payment to transaction
        transaction.payment_id = payment.id
        db.session.commit()
        
        return payment
    except Exception as e:
        db.session.rollback()
        raise e

def submit_for_approval(transaction_id):
    """Submit transaction for lawyer approval"""
    transaction = TransactionItem.query.get(transaction_id)
    if transaction:
        # For case transactions, create document and set status
        if transaction.transaction_type == 'Case':
            create_case_document(transaction)
        db.session.commit()
    return transaction

def approve_transaction(transaction_id, lawyer_notes=None):
    """Lawyer approves transaction"""
    transaction = TransactionItem.query.get(transaction_id)
    if transaction:
        # Auto-create NotarialEntry if notarial transaction
        if transaction.transaction_type == 'Notarial':
            create_notarial_entry(transaction)
        db.session.commit()
    return transaction

def complete_transaction(transaction_id):
    """Mark transaction as completed"""
    transaction = TransactionItem.query.get(transaction_id)
    if transaction:
        # Update any related documents
        if transaction.transaction_type == 'Case':
            document = CaseDocument.query.filter_by(transaction_item_id=transaction.id).first()
            if document:
                document.document_status = 'Completed'  # Use the correct field name
        db.session.commit()
    return transaction

def mark_payment_paid(transaction_id, payment_method, payment_reference):
    """Mark payment as paid and update transaction AND notarial entry"""
    transaction = TransactionItem.query.get(transaction_id)
    if transaction:
        # Update transaction
        transaction.payment_status = 'Paid'
        transaction.payment_date = datetime.now(PHT)
        
        # If this is a notarial transaction, also update the notarial entry
        if transaction.transaction_type == 'Notarial':
            notarial_entry = NotarialEntry.query.filter_by(
                transaction_item_id=transaction.id
            ).first()
            
            if notarial_entry:
                notarial_entry.transaction_status = 'paid'
                # Also update OR number if provided in payment reference
                if payment_reference and 'OR' in payment_reference:
                    notarial_entry.not_fee_or = payment_reference
        
        # Update payment record if exists
        if transaction.payment:
            transaction.payment.payment_status = 'Paid'
            transaction.payment.pay_method = payment_method
            transaction.payment.pay_ref = payment_reference
            transaction.payment.pay_date = datetime.utcnow()
        
        db.session.commit()
    return transaction

def create_case_document(transaction):
    """Auto-create CaseDocument for case transactions"""
    try:
        document = CaseDocument(
            filename=f"Case_Transaction_{transaction.id}",  # Create a meaningful filename
            file_path=f"/transactions/case_{transaction.id}",  # Temporary path
            document_type='Transaction Record',
            document_status='Draft',
            case_id=transaction.case_id,  # Use the case_id from transaction
            transaction_item_id=transaction.id  # Link to transaction
        )
        db.session.add(document)
        return document
    except Exception as e:
        db.session.rollback()
        raise e

def create_notarial_entry(transaction):
    """Auto-create NotarialEntry for notarial transactions"""
    try:
        client = transaction.client
        entry = NotarialEntry(
            not_entry_num=f"NOTARY-{transaction.id}-{datetime.utcnow().strftime('%Y%m%d')}",
            not_title=transaction.purpose,
            not_date=datetime.now(PHT),
            not_party_name=client.full_name,
            transaction_item_id=transaction.id
        )
        db.session.add(entry)
        return entry
    except Exception as e:
        db.session.rollback()
        raise e

def is_notarization_service(service_id):
    """Check if service is a notarization service"""
    service = Service.query.get(service_id)
    return service and service.is_notarization

def get_all_transactions():
    """Get all transactions with proper display logic"""
    transactions = TransactionItem.query.options(
        db.joinedload(TransactionItem.client),
        db.joinedload(TransactionItem.service),
        db.joinedload(TransactionItem.case)  # Load case relationship
    ).all()
    
    # For notarial transactions, check if they're linked to a paid entry
    for transaction in transactions:
        if transaction.transaction_type == 'Notarial':
            # Get the linked notarial entry
            notarial_entry = NotarialEntry.query.filter_by(
                transaction_item_id=transaction.id
            ).first()
            
            if notarial_entry:
                # Set entry_reference in transaction
                transaction.entry_reference = f"{notarial_entry.not_book_num}-{notarial_entry.not_page_num}-{notarial_entry.not_entry_num}"
                
                # Override the transaction payment status if entry is paid
                if notarial_entry.transaction_status == 'paid':
                    transaction.payment_status = 'Paid'
        elif transaction.transaction_type == 'Case':
            # Set display fields for case transactions
            if transaction.case:
                transaction.case_reference = transaction.case.case_number
                transaction.client_display = transaction.client.full_name if transaction.client else "Unknown Client"
    
    return transactions

def sync_notarial_entry_payment_status(transaction_id):
    """Sync payment status from notarial entry to transaction"""
    transaction = TransactionItem.query.get(transaction_id)
    if not transaction or transaction.transaction_type != 'Notarial':
        return None
    
    notarial_entry = NotarialEntry.query.filter_by(
        transaction_item_id=transaction.id
    ).first()
    
    if notarial_entry:
        # Sync payment status from entry to transaction
        if notarial_entry.transaction_status == 'paid':
            transaction.payment_status = 'Paid'
            if not transaction.payment_date:
                transaction.payment_date = datetime.now(PHT)
        else:
            transaction.payment_status = 'Pending'
        
        db.session.commit()
    
    return transaction

def sync_existing_notarial_payments():
    """Sync payment status for all existing notarial entries and transactions"""
    notarial_entries = NotarialEntry.query.all()
    
    for entry in notarial_entries:
        if entry.transaction_item_id:
            transaction = TransactionItem.query.get(entry.transaction_item_id)
            if transaction:
                # Sync based on OR number
                if entry.not_fee_or and entry.not_fee_or.strip():
                    entry.transaction_status = 'paid'
                    transaction.payment_status = 'Paid'
                    if not transaction.payment_date:
                        transaction.payment_date = entry.not_date or datetime.now(timezone.utc)
                else:
                    entry.transaction_status = 'unpaid'
                    transaction.payment_status = 'Pending'
    
    db.session.commit()
    print(f"Synced {len(notarial_entries)} notarial entries with transactions")


def format_transaction_display(transaction):
    """
    Format transaction for display based on type
    
    Args:
        transaction (TransactionItem): The transaction
    
    Returns:
        dict: Formatted display data
    """
    if transaction.transaction_type == 'Notarial':
        # Get entry reference
        notarial_entry = NotarialEntry.query.filter_by(
            transaction_item_id=transaction.id
        ).first()
        
        if notarial_entry:
            display = {
                'reference': f"{notarial_entry.not_book_num}-{notarial_entry.not_page_num}-{notarial_entry.not_entry_num}",
                'description': f"Notarial: {notarial_entry.not_title}",
                'client_display': "N/A"  # Notarial entries don't show client name
            }
        else:
            display = {
                'reference': f"Notarial #{transaction.id}",
                'description': transaction.purpose,
                'client_display': "N/A"
            }
    
    elif transaction.transaction_type == 'Case':
        display = {
            'reference': transaction.case.case_number if transaction.case else f"Case #{transaction.id}",
            'description': transaction.purpose,
            'client_display': transaction.client.full_name if transaction.client else "Unknown Client"
        }
    
    else:
        display = {
            'reference': f"#{transaction.id}",
            'description': transaction.purpose,
            'client_display': transaction.client.full_name if transaction.client else "Unknown Client"
        }
    
    return display