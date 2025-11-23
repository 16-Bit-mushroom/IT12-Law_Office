# routes/settings.py
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from app.services.user_service import (
    get_all_users, get_user_by_id, create_new_user, 
    update_user_profile_admin, delete_user, activate_user
)

settings_bp = Blueprint('settings', __name__, url_prefix='/settings')

@settings_bp.route('')
@login_required
def settings_page():
    """Main settings page"""
    if not current_user.is_admin:
        flash('Access denied. Administrator privileges required.', 'error')
        return redirect(url_for('dashboard.dashboard_page'))
    
    users = get_all_users()
    return render_template('settings_page.html', users=users)

@settings_bp.route('/users/data')
@login_required
def get_users_data():
    """Get users data for AJAX requests"""
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    users = get_all_users()
    return jsonify([user.to_dict() for user in users])

@settings_bp.route('/users/<int:user_id>')
@login_required
def get_user(user_id):
    """Get specific user data"""
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    user = get_user_by_id(user_id)
    if user:
        return jsonify(user.to_dict())
    return jsonify({'error': 'User not found'}), 404

@settings_bp.route('/users/create', methods=['POST'])
@login_required
def create_user():
    """Create a new user"""
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    data = request.get_json()
    
    success, message = create_new_user(
        username=data.get('username'),
        email=data.get('email'),
        password=data.get('password'),
        contact_number=data.get('contact_number'),
        role=data.get('role', 'attorney'),
        is_admin=data.get('is_admin', False)
    )
    
    return jsonify({'success': success, 'message': message})

@settings_bp.route('/users/<int:user_id>/update', methods=['POST'])
@login_required
def update_user(user_id):
    """Update an existing user"""
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    data = request.get_json()
    
    success, message = update_user_profile_admin(
        user_id=user_id,
        username=data.get('username'),
        email=data.get('email'),
        contact_number=data.get('contact_number'),
        role=data.get('role'),
        is_admin=data.get('is_admin', False),
        is_active=data.get('is_active', True)
    )
    
    return jsonify({'success': success, 'message': message})

@settings_bp.route('/users/<int:user_id>/deactivate', methods=['POST'])
@login_required
def deactivate_user(user_id):
    """Deactivate a user"""
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    success, message = delete_user(user_id)
    return jsonify({'success': success, 'message': message})

@settings_bp.route('/users/<int:user_id>/activate', methods=['POST'])
@login_required
def reactivate_user(user_id):
    """Reactivate a user"""
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    success, message = activate_user(user_id)
    return jsonify({'success': success, 'message': message})