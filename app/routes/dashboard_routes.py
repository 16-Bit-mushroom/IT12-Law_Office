from flask import Blueprint, render_template, url_for
from flask_login import login_required
from sqlalchemy import func
from sqlalchemy.orm import joinedload
from app.models.notarial_entry_mdl import NotarialEntry


# Adjust these imports to match your actual folder structure
# e.g., from app.models.document_mdl import Document
from app import db
from app.models.client_mdl import Client
from app.models.document_mdl import Document
from app.models.case_mdl import Case
from app.models.transaction_mdl import TransactionItem

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/')

def resolve_document_context(doc):
    """
    Helper to find the 'Human Readable' context for a document.
    Returns a string like 'Case #101' or 'Client: John Doe'.
    """
    if not doc.parent_type or not doc.parent_id:
        return "General Upload"

    try:
        if doc.parent_type == 'case':
            case = Case.query.get(doc.parent_id)
            return f"Case: {case.title}" if case else "Unknown Case"
        elif doc.parent_type == 'client':
            client = Client.query.get(doc.parent_id)
            return f"Client: {client.last_name}, {client.first_name}" if client else "Unknown Client"
        elif doc.parent_type == 'notarial_entry':  # ADD THIS SECTION
            from app.models.notarial_entry_mdl import NotarialEntry
            entry = NotarialEntry.query.get(doc.parent_id)
            if entry:
                # Get first party name or use entry number as fallback
                if entry.parties and len(entry.parties) > 0:
                    return f"Notary: {entry.parties[0].party_name}"
                else:
                    return f"Notary Entry #{entry.not_entry_num}"
            else:
                return "Unknown Notarial Entry"
        elif doc.parent_type == 'transaction':
            # hypothetical, based on your system structure
            return f"Transaction #{doc.parent_id}"
    except Exception as e:
        print(f"Error resolving context: {e}")  # For debugging
        return f"{doc.parent_type.title()} #{doc.parent_id}"
    
    return f"{doc.parent_type} #{doc.parent_id}"

# --- Helper 2: Smart URL Routing ---
# dashboard_routes.py - Fix get_context_url function
def get_context_url(doc):
    """
    Returns the URL to the PARENT view (Case Detail / Notary Detail)
    instead of just the document view.
    """
    if doc.parent_type == 'case':
        # Points to the Case Detail page
        return f"/cases/{doc.parent_id}" 
    elif doc.parent_type == 'notarial_entry':
        # FIXED: Use the notarial_entries.entry_details route
        return url_for('notarial_entries.entry_details', entry_id=doc.parent_id)  # CHANGED THIS LINE
    elif doc.parent_type == 'client':
        # Points to Client Profile
        return f"/clients/{doc.parent_id}"
    
    # Default fallback if no parent context exists
    return f"/documents/{doc.id}"

@dashboard_bp.route('/')
@dashboard_bp.route('/dashboard')
@login_required 
def dashboard_page():
    # --- KPI 1: DOCUMENTS ---
    # Count total documents
    total_docs = Document.query.count()
    # Count docs tagged as 'Lacking' (as per your model comments)
    missing_docs = Document.query.filter(Document.document_status.ilike('Lacking')).count()

    # --- KPI 2: WORKFLOW STATUS ---
    # Use payment_status instead of transaction_status
    # Count pending payments (transactions with payment_status = 'Pending')
    pending_payments_count = TransactionItem.query.filter_by(payment_status='Pending').count()
    
    # For documents, keep existing logic
    pending_docs_count = Document.query.filter(Document.document_status.ilike('Pending')).count()
    
    # Total pending = pending documents + pending payments
    total_pending = pending_docs_count + pending_payments_count

    # --- KPI 3: FINANCIALS ---
    # Sum transaction_amount where payment_status is 'Pending'
    unpaid_sum = db.session.query(func.sum(TransactionItem.transaction_amount))\
        .filter(TransactionItem.payment_status == 'Pending').scalar() or 0
    
    # Count number of unpaid transactions
    unpaid_count = TransactionItem.query.filter_by(payment_status='Pending').count()

    # --- KPI 4: ACTIVE MATTERS ---
    # Count cases where status is 'active'
    open_cases = Case.query.filter(Case.status.ilike('active')).count()

    # --- NEW KPI: Transaction Types ---
    notarial_count = TransactionItem.query.filter_by(transaction_type='Notarial').count()
    case_count = TransactionItem.query.filter_by(transaction_type='Case').count()

    # Package data for the template
    kpi_data = {
        'total_docs': total_docs,
        'missing_docs': missing_docs,
        'pending_review': total_pending,
        'pending_payments': pending_payments_count,  # New: specifically track pending payments
        'total_unpaid': "{:,.2f}".format(unpaid_sum), # Format as currency string
        'unpaid_count': unpaid_count,
        'open_cases': open_cases,
        'notarial_count': notarial_count,  # New: notarial transactions count
        'case_count': case_count  # New: case transactions count
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

    # In dashboard_routes.py, update the section for pending transactions:

    # Add recent pending transactions to action items
    pending_transactions = TransactionItem.query\
        .filter_by(payment_status='Pending')\
        .options(joinedload(TransactionItem.client))\
        .order_by(TransactionItem.transaction_date.desc())\
        .limit(5).all()

    action_transactions_data = []
    for transaction in pending_transactions:
        # SAFELY get client name - handle the case where client might be None
        client_name = "Unknown Client"
        if transaction.client and hasattr(transaction.client, 'full_name'):
            client_name = transaction.client.full_name
        
        action_transactions_data.append({
            'title': f"{transaction.purpose} - {client_name}",
            'context': f"{transaction.transaction_type} Transaction",
            'status': 'Pending Payment',
            'id': transaction.id,
            'target_url': url_for('transaction.transactions_page')  # Link to transactions page
        })

    context = {
        'kpi': kpi_data,
        'action_docs': action_docs_data,
        'action_transactions': action_transactions_data  # New: pending transactions for action
    }

    return render_template('dashboard_page.html', **context)