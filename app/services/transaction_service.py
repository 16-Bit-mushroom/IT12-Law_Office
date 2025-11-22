from app.models import db
from app.models.transaction_mdl import TransactionItem
from app.models.payment_mdl import Payment
from app.models.case_logs_mdl import CaseDocument
from app.models.notarial_entry_mdl import NotarialEntry
from app.models.service_mdl import Service
import uuid
from datetime import datetime

def create_transaction(transaction_data):
    """Create a new transaction with automated workflow connections"""
    try:
        transaction = TransactionItem(
            client_id=transaction_data['client_id'],
            service_id=transaction_data['service_id'],
            transaction_amount=transaction_data['amount'],
            document_title=transaction_data.get('document_title'),
            document_purpose=transaction_data.get('document_purpose'),
            transaction_status='Draft'
        )
        db.session.add(transaction)
        db.session.commit()
        
        # Auto-create pending payment (Conditional Automation from your analysis)
        create_pending_payment(transaction)
        
        return transaction
    except Exception as e:
        db.session.rollback()
        raise e

def create_pending_payment(transaction):
    """Auto-create a pending payment record for a transaction"""
    try:
        payment = Payment(
            pay_method='Pending',
            pay_ref=f"INV-{transaction.id}-{uuid.uuid4().hex[:8].upper()}",
            pay_type='Document Service',
            pay_amount=transaction.transaction_amount,
            payment_status='Pending'
        )
        db.session.add(payment)
        db.session.flush()  # Get the payment ID without committing
        
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
        transaction.transaction_status = 'Pending Approval'
        db.session.commit()
    return transaction

def approve_transaction(transaction_id, lawyer_notes=None):
    """Lawyer approves transaction and auto-creates documents"""
    transaction = TransactionItem.query.get(transaction_id)
    if transaction:
        transaction.transaction_status = 'Approved'
        transaction.approved_date = datetime.utcnow()
        transaction.lawyer_notes = lawyer_notes
        db.session.commit()
        
        # Auto-create CaseDocument upon approval (Conditional Automation)
        create_case_document(transaction)
        
        # Auto-create NotarialEntry if service is notarization
        if is_notarization_service(transaction.service_id):
            create_notarial_entry(transaction)
    
    return transaction

def complete_transaction(transaction_id):
    """Mark transaction as completed after printing/signing"""
    transaction = TransactionItem.query.get(transaction_id)
    if transaction:
        transaction.transaction_status = 'Completed'
        transaction.completed_date = datetime.utcnow()
        db.session.commit()
    return transaction

def mark_payment_paid(payment_id, payment_method, payment_reference):
    """Mark payment as paid and update transaction status"""
    payment = Payment.query.get(payment_id)
    if payment:
        payment.payment_status = 'Paid'
        payment.pay_method = payment_method
        payment.pay_ref = payment_reference
        payment.pay_date = datetime.utcnow()
        
        # Update related transaction payment status
        transaction = TransactionItem.query.filter_by(payment_id=payment_id).first()
        if transaction:
            transaction.payment_status = 'Paid'
        
        db.session.commit()
    return payment

def create_case_document(transaction):
    """Auto-create CaseDocument when transaction is approved"""
    try:
        document = CaseDocument(
            cas_doc_name=transaction.document_title or f"Document for Transaction #{transaction.id}",
            cas_doc_status='Draft',
            client_id=transaction.client_id,
            transaction_item_id=transaction.id
        )
        db.session.add(document)
        db.session.commit()
        return document
    except Exception as e:
        db.session.rollback()
        raise e

def create_notarial_entry(transaction):
    """Auto-create NotarialEntry for notarization services"""
    try:
        client = transaction.client
        entry = NotarialEntry(
            not_entry_num=f"NOTARY-{transaction.id}-{datetime.utcnow().strftime('%Y%m%d')}",
            not_title=transaction.document_title or "Notarized Document",
            not_date=datetime.utcnow(),
            not_party_name=client.full_name,
            transaction_item_id=transaction.id
        )
        db.session.add(entry)
        db.session.commit()
        
        # Auto-update document status to "Notarized" (Automatic connection)
        document = CaseDocument.query.filter_by(transaction_item_id=transaction.id).first()
        if document:
            document.cas_doc_status = 'Notarized'
            db.session.commit()
            
        return entry
    except Exception as e:
        db.session.rollback()
        raise e

def is_notarization_service(service_id):
    """Check if service is a notarization service"""
    service = Service.query.get(service_id)
    if service and service.service_name:
        # Check if the service name contains 'notarization' or related terms
        notary_terms = ['notarization', 'notary', 'notarial']
        return any(term in service.service_name.lower() for term in notary_terms)
    return False

def get_all_transactions():
    """Get all transactions with client and service info"""
    return TransactionItem.query.all()