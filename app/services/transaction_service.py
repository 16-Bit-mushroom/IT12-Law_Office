from app.models import db
from app.models.transaction_mdl import TransactionItem
from app.models.payment_mdl import Payment
from app.models.case_logs_mdl import CaseDocument
from app.models.notarial_entry_mdl import NotarialEntry
from app.models.service_mdl import Service
import uuid
from datetime import datetime


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
            payment_status='Pending'
        )
        db.session.add(transaction)
        db.session.commit()
        
        # Auto-create pending payment
        create_pending_payment(transaction)
        
        return transaction
    except Exception as e:
        db.session.rollback()
        raise e

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
                document.cas_doc_status = 'Completed'
        db.session.commit()
    return transaction

def mark_payment_paid(transaction_id, payment_method, payment_reference):
    """Mark payment as paid and update transaction"""
    transaction = TransactionItem.query.get(transaction_id)
    if transaction and transaction.payment:
        transaction.payment.payment_status = 'Paid'
        transaction.payment.pay_method = payment_method
        transaction.payment.pay_ref = payment_reference
        transaction.payment.pay_date = datetime.utcnow()
        transaction.payment_status = 'Paid'
        transaction.payment_date = datetime.utcnow()
        
        db.session.commit()
    return transaction

def create_case_document(transaction):
    """Auto-create CaseDocument for case transactions"""
    try:
        document = CaseDocument(
            cas_doc_name=transaction.purpose,
            cas_doc_status='Draft',
            client_id=transaction.client_id,
            transaction_item_id=transaction.id
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
            not_date=datetime.utcnow(),
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
    """Get all transactions with client and service info"""
    return TransactionItem.query.options(
        db.joinedload(TransactionItem.client),
        db.joinedload(TransactionItem.service)
    ).all()