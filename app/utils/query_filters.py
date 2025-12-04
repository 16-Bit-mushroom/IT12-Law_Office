# app/utils/query_filters.py
from flask_login import current_user

def filter_for_user(query, model):
    """Apply role-based filters to queries"""
    if not current_user.is_authenticated:
        return query.filter(False)  # No data for unauthenticated users
    
    if current_user.is_admin or current_user.role == 'admin':
        return query  # Admin sees everything
    
    if current_user.role == 'staff':
        # Staff only sees notarial data
        
        # Filter for TransactionItem
        if hasattr(model, 'transaction_type') and hasattr(model, 'id'):
            return query.filter(model.transaction_type == 'Notarial')
        
        # Filter for Document
        if hasattr(model, 'parent_type') and hasattr(model, 'id'):
            return query.filter(model.parent_type == 'notarial_entry')
        
        # For other models, return empty query
        return query.filter(False)
    
    return query.filter(False)

def get_accessible_transactions():
    """Get transactions accessible to current user"""
    from app.models.transaction_mdl import TransactionItem
    
    query = TransactionItem.query
    
    if current_user.role == 'staff':
        return query.filter(TransactionItem.transaction_type == 'Notarial')
    
    return query

def get_accessible_documents():
    """Get documents accessible to current user"""
    from app.models.document_mdl import Document
    
    query = Document.query
    
    if current_user.role == 'staff':
        return query.filter(Document.parent_type == 'notarial_entry')
    
    return query

def get_accessible_cases():
    """Get cases accessible to current user"""
    from app.models.case_mdl import Case
    
    query = Case.query
    
    if current_user.role == 'staff':
        # Staff cannot see any cases
        return query.filter(False)
    
    return query

def filter_dashboard_data():
    """Filter dashboard data based on user role"""
    from app.models.document_mdl import Document
    from app.models.transaction_mdl import TransactionItem
    from app.models.case_mdl import Case
    
    if current_user.role == 'staff':
        # Staff only sees notarial data
        return {
            'documents': Document.query.filter(Document.parent_type == 'notarial_entry'),
            'transactions': TransactionItem.query.filter(TransactionItem.transaction_type == 'Notarial'),
            'cases': Case.query.filter(False)  # No cases
        }
    
    # Admin sees everything
    return {
        'documents': Document.query,
        'transactions': TransactionItem.query,
        'cases': Case.query
    }