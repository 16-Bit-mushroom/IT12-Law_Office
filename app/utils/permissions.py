# app/utils/permissions.py
from functools import wraps
from flask import abort, flash, redirect, url_for, request
from flask_login import current_user

def admin_required(f):
    """Admin only access decorator"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please login to access this page.', 'error')
            return redirect(url_for('auth.login'))
        if not current_user.is_admin and current_user.role != 'admin':
            flash('Administrator access required.', 'error')
            return redirect(url_for('dashboard.dashboard_page'))
        return f(*args, **kwargs)
    return decorated_function

def staff_or_admin_required(f):
    """Staff or Admin access decorator"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please login to access this page.', 'error')
            return redirect(url_for('auth.login'))
        if current_user.role not in ['admin', 'staff']:
            flash('Staff or Administrator access required.', 'error')
            return redirect(url_for('dashboard.dashboard_page'))
        return f(*args, **kwargs)
    return decorated_function

def can_access_module(module_name):
    """Check if user can access a specific module"""
    if not current_user.is_authenticated:
        return False
    
    if current_user.is_admin or current_user.role == 'admin':
        return True
    
    if current_user.role == 'staff':
        # Staff can only access notarial-related modules
        notarial_modules = ['notarial_entries', 'documents', 'transaction']
        return module_name in notarial_modules
    
    return False

def can_access_case():
    """Check if user can access case-related data"""
    return current_user.is_authenticated and (current_user.is_admin or current_user.role == 'admin')

def can_access_notarial():
    """Check if user can access notarial data"""
    return current_user.is_authenticated and current_user.role in ['admin', 'staff']

def check_notarial_access(parent_type=None, parent_id=None):
    """Check if staff can access specific notarial resource"""
    if not current_user.is_authenticated:
        return False
    
    if current_user.is_admin or current_user.role == 'admin':
        return True
    
    if current_user.role == 'staff':
        # Staff can only access notarial entries and their documents
        allowed_types = ['notarial_entry', 'notarial']
        return parent_type in allowed_types if parent_type else True
    
    return False

def block_staff_from_cases():
    """Block staff from accessing case-related data"""
    if current_user.is_authenticated and current_user.role == 'staff':
        flash('Access to case data is restricted to administrators only.', 'error')
        return redirect(url_for('dashboard.dashboard_page'))
    return None