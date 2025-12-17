# app/routes/dashboard_routes.py
from flask import Blueprint, render_template, url_for
from flask_login import login_required, current_user
from sqlalchemy import func, or_
from datetime import datetime, timedelta, date
from sqlalchemy.orm import joinedload
from app import db

# Models
from app.models.client_mdl import Client
from app.models.document_mdl import Document
from app.models.case_mdl import Case
from app.models.schedule_mdl import Schedule
from app.models.transaction_mdl import TransactionItem
from app.models.notarial_entry_mdl import NotarialEntry
from app.utils.query_filters import filter_dashboard_data

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/')

def resolve_document_context(doc):
    """Helper to get readable context for a document"""
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
            entry = NotarialEntry.query.get(doc.parent_id)
            if entry:
                return f"Notarial: {entry.not_title}"
            return "Unknown Entry"
        return f"{doc.parent_type} #{doc.parent_id}"
    except Exception:
        return "Unknown Context"

def get_monthly_growth(model, date_field):
    """
    Helper to calculate current month count vs last month count
    Returns: (current_count, percent_change, trend_direction)
    """
    today = date.today()
    first_day_this_month = today.replace(day=1)
    # Handle January edge case for previous month
    if first_day_this_month.month == 1:
        first_day_last_month = first_day_this_month.replace(year=today.year - 1, month=12)
    else:
        first_day_last_month = first_day_this_month.replace(month=today.month - 1)
    
    # Current Month Count
    current_count = model.query.filter(
        getattr(model, date_field) >= first_day_this_month
    ).count()
    
    # Last Month Count
    last_count = model.query.filter(
        getattr(model, date_field) >= first_day_last_month,
        getattr(model, date_field) < first_day_this_month
    ).count()
    
    # Calculate Growth
    if last_count == 0:
        percent = 100 if current_count > 0 else 0
    else:
        percent = int(((current_count - last_count) / last_count) * 100)
        
    return current_count, percent, last_count

@dashboard_bp.route('/')
@dashboard_bp.route('/dashboard')
@login_required 
def dashboard_page():
    # --- 1. NEW KPI CALCULATIONS ---
    
    # KPI 1: Case Intake (Growth)
    new_cases_count, case_growth, _ = get_monthly_growth(Case, 'created_at')
    
    # KPI 2: Client Growth
    new_clients_count, client_growth, _ = get_monthly_growth(Client, 'created_at')
    total_clients = Client.query.filter_by(is_active=True).count()
    
    # KPI 3: Backlog Health (Pending Reviews)
    pending_reviews_count = Document.query.filter(
        or_(Document.document_status.ilike('Pending'), 
            Document.document_status.ilike('For Signature')),
        Document.deleted_at == None
    ).count()
    backlog_target = 5
    
    # KPI 4: Notarial Volume
    notarial_this_month, notarial_growth, _ = get_monthly_growth(NotarialEntry, 'not_date')

    # Construct the KPI Dictionary for the template
    kpi_data = {
        'cases': {
            'value': new_cases_count,
            'growth': case_growth,
            'target': 5,
            'trend': 'up' if case_growth >= 0 else 'down'
        },
        'clients': {
            'value': total_clients,
            'new_this_month': new_clients_count,
            'growth': client_growth,
            'trend': 'up' if client_growth >= 0 else 'down'
        },
        'backlog': {
            'value': pending_reviews_count,
            'target': backlog_target,
            'is_critical': pending_reviews_count > 8
        },
        'notarial': {
            'value': notarial_this_month,
            'growth': notarial_growth,
            'trend': 'up' if notarial_growth >= 0 else 'down'
        }
    }

    # --- 2. BOTTOM PANELS DATA ---

    # A. Documents Requiring Action (List Generation)
    pending_docs = Document.query.filter(
        or_(Document.document_status.ilike('Pending'),
            Document.document_status.ilike('Lacking'),
            Document.document_status.ilike('For Signature')),
        Document.deleted_at == None
    ).order_by(Document.uploaded_at.desc()).limit(5).all()

    action_docs_data = []
    for doc in pending_docs:
        context = resolve_document_context(doc)
        # Determine target URL based on parent type
        if doc.parent_type == 'case':
            target_url = url_for('case.view_case', case_id=doc.parent_id)
        elif doc.parent_type == 'notarial_entry':
            target_url = url_for('notarial_entries.entry_details', entry_id=doc.parent_id)
        else:
            target_url = "#" # Fallback

        action_docs_data.append({
            'title': doc.filename,
            'context': context,
            'status': doc.document_status,
            'id': doc.id,
            'target_url': target_url
        })

    # B. Transactions Requiring Action (List Generation)
    if current_user.role == 'staff':
        # Staff logic (example: filter by created_by if applicable, otherwise all)
        pending_transactions = TransactionItem.query\
            .filter_by(payment_status='Pending')\
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

    # C. Upcoming Deadlines
    upcoming_deadlines = Schedule.query\
        .options(joinedload(Schedule.case))\
        .filter(Schedule.is_done == False)\
        .order_by(Schedule.deadline.asc())\
        .limit(6).all()

    # D. Recent Notarials (New Panel)
    recent_notarials = NotarialEntry.query\
        .order_by(NotarialEntry.not_date.desc())\
        .limit(5).all()

    # --- 3. DAILY BRIEFING LOGIC ---
    today = date.today()
    three_days_later = today + timedelta(days=3)
    
    urgent_deadlines = Schedule.query\
        .options(joinedload(Schedule.case))\
        .filter(Schedule.is_done == False)\
        .filter(Schedule.deadline >= today)\
        .filter(Schedule.deadline <= three_days_later)\
        .order_by(Schedule.deadline.asc())\
        .all()
        
    # Show modal if there are urgent deadlines OR pending reviews > 0
    show_briefing = (len(urgent_deadlines) > 0) or (pending_reviews_count > 0)

    # --- 4. RENDER ---
    context = {
        'kpi': kpi_data,
        'action_docs': action_docs_data,
        'action_transactions': action_transactions_data,
        'upcoming_deadlines': upcoming_deadlines,
        'recent_notarials': recent_notarials,
        
        # Briefing variables
        'urgent_deadlines': urgent_deadlines,
        'urgent_reviews': pending_reviews_count,
        'show_briefing': show_briefing,
        'now': date.today()
    }

    return render_template('dashboard_page.html', **context)