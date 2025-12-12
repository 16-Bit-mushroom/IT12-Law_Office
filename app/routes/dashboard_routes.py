# app/routes/dashboard_routes.py
from flask import Blueprint, render_template, url_for
from flask_login import login_required, current_user
from sqlalchemy import func
from datetime import datetime
from sqlalchemy.orm import joinedload
from app import db
from app.models.client_mdl import Client
from app.models.document_mdl import Document
from app.models.case_mdl import Case
from app.models.schedule_mdl import Schedule
from app.models.transaction_mdl import TransactionItem
# REMOVED: from app.models.system_log_mdl import SystemLog
from app.utils.query_filters import filter_dashboard_data

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/')

def resolve_document_context(doc):
    if not doc.parent_type or not doc.parent_id:
        return "General Upload"
    try:
        if doc.parent_type == 'case':
            case = Case.query.get(doc.parent_id)
            return f"Case: {case.title}" if case else "Unknown Case"
        elif doc.parent_type == 'client':
            client = Client.query.get(doc.parent_id)
            return f"Client: {client.client_last_name}, {client.client_first_name}" if client else "Unknown Client"
        elif doc.parent_type == 'notarial_entry':
            from app.models.notarial_entry_mdl import NotarialEntry
            entry = NotarialEntry.query.get(doc.parent_id)
            if entry:
                if entry.parties and len(entry.parties) > 0:
                    return f"Notary: {entry.parties[0].party_name}"
                else:
                    return f"Notary Entry #{entry.not_entry_num}"
            else:
                return "Unknown Notarial Entry"
    except Exception as e:
        return f"{doc.parent_type.title()} #{doc.parent_id}"
    return f"{doc.parent_type} #{doc.parent_id}"

def get_context_url(doc):
    if doc.parent_type == 'case':
        return f"/cases/{doc.parent_id}" 
    elif doc.parent_type == 'notarial_entry':
        return url_for('notarial_entries.entry_details', entry_id=doc.parent_id)
    elif doc.parent_type == 'client':
        return f"/clients/{doc.parent_id}"
    return f"/documents/{doc.id}"

@dashboard_bp.route('/')
@dashboard_bp.route('/dashboard')
@login_required 
def dashboard_page():
    filtered_data = filter_dashboard_data()
    
    total_docs = filtered_data['documents'].count()
    missing_docs = filtered_data['documents'].filter(Document.document_status.ilike('Lacking')).count()
    
    if current_user.role == 'staff':
        pending_payments_count = filtered_data['transactions'].filter_by(payment_status='Pending').count()
        unpaid_sum = db.session.query(func.sum(TransactionItem.transaction_amount))\
            .filter(TransactionItem.payment_status == 'Pending',
                   TransactionItem.transaction_type == 'Notarial').scalar() or 0
        unpaid_count = TransactionItem.query.filter_by(
            payment_status='Pending', 
            transaction_type='Notarial'
        ).count()
    else:
        pending_payments_count = TransactionItem.query.filter_by(payment_status='Pending').count()
        unpaid_sum = db.session.query(func.sum(TransactionItem.transaction_amount))\
            .filter(TransactionItem.payment_status == 'Pending').scalar() or 0
        unpaid_count = TransactionItem.query.filter_by(payment_status='Pending').count()
    
    pending_docs_count = Document.query.filter(Document.document_status.ilike('Pending')).count()
    total_pending = pending_docs_count + pending_payments_count
    open_cases = Case.query.filter(Case.status.ilike('active')).count()
    notarial_count = TransactionItem.query.filter_by(transaction_type='Notarial').count()
    case_count = TransactionItem.query.filter_by(transaction_type='Case').count()
    
    upcoming_deadlines = Schedule.query\
        .options(joinedload(Schedule.case))\
        .filter(Schedule.is_done == False)\
        .order_by(Schedule.deadline.asc())\
        .limit(6)\
        .all()
    
    # REMOVED: recent_logs query

    kpi_data = {
        'total_docs': total_docs,
        'missing_docs': missing_docs,
        'pending_review': total_pending,
        'pending_payments': pending_payments_count,
        'total_unpaid': "{:,.2f}".format(unpaid_sum),
        'unpaid_count': unpaid_count,
        'open_cases': open_cases,
        'notarial_count': notarial_count,
        'case_count': case_count
    }
    
    action_docs_query = Document.query.filter(
        Document.document_status.in_(['Pending', 'Lacking', 'Draft', 'For Signature'])
    ).order_by(
        db.case((Document.document_status == 'Lacking', 1), else_=2),
        Document.last_modified.desc()
    ).limit(5).all()

    action_docs_data = []
    for doc in action_docs_query:
        action_docs_data.append({
            'title': doc.document_type or doc.filename,
            'context': resolve_document_context(doc),
            'status': doc.document_status,
            'id': doc.id,
            'target_url': get_context_url(doc)
        })

    if current_user.role == 'staff':
        pending_transactions = TransactionItem.query\
            .filter_by(payment_status='Pending', transaction_type='Notarial')\
            .options(joinedload(TransactionItem.client))\
            .order_by(TransactionItem.transaction_date.desc())\
            .limit(5).all()
    else:
        pending_transactions = TransactionItem.query\
            .filter_by(payment_status='Pending')\
            .options(joinedload(TransactionItem.client))\
            .order_by(TransactionItem.transaction_date.desc())\
            .limit(5).all()

    action_transactions_data = []
    for transaction in pending_transactions:
        client_name = "Unknown Client"
        if transaction.client:
            # Handle potential different naming conventions based on your Client model
            if hasattr(transaction.client, 'full_name'):
                client_name = transaction.client.full_name
            elif hasattr(transaction.client, 'client_first_name'):
                client_name = f"{transaction.client.client_first_name} {transaction.client.client_last_name}"
        
        action_transactions_data.append({
            'title': f"{transaction.purpose} - {client_name}",
            'context': f"{transaction.transaction_type} Transaction",
            'status': 'Pending Payment',
            'id': transaction.id,
            'target_url': url_for('transaction.transactions_page')
        })

    context = {
        'kpi': kpi_data,
        'action_docs': action_docs_data,
        'action_transactions': action_transactions_data,
        'upcoming_deadlines': upcoming_deadlines,
        # REMOVED: 'recent_logs': recent_logs,
        'now': datetime.now().date()
    }

    return render_template('dashboard_page.html', **context)