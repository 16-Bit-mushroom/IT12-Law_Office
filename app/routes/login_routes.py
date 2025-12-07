from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import current_user, login_required
from app.services.auth_service import authenticate_user, deauthenticate_user

from app.services.system_log_service import SystemLogService

# Changed to 'auth' for clarity and to avoid conflicts
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    # If the user is already logged in, redirect them away from the login page
    if current_user.is_authenticated:
        # Send authenticated users to the main dashboard
        return redirect(url_for('dashboard.dashboard_page'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        success, result = authenticate_user(email, password)
        
        if success:
            
            # --- LOGGING START ---
            SystemLogService.log(
                action='Login',
                module='Auth',
                description=f"User '{result.username}' logged in successfully.",
                entity_id=result.id
            )
            # --- LOGGING END ---
            
            flash(f'Welcome back, {result.username}!', 'success')
            # Redirect to the page they were trying to access, or the dashboard
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard.dashboard_page'))
        else:
            flash(result, 'danger')
            
    return render_template('login_page.html')

@auth_bp.route('/logout')
@login_required # Ensures only logged-in users can log out
def logout():
    
    # --- LOGGING START ---
    SystemLogService.log(
        action='Logout',
        module='Auth',
        description=f"User '{current_user.username}' logged out.",
        entity_id=current_user.id
    )
    # --- LOGGING END ---
    message = deauthenticate_user()
    flash(message, 'info')
    return redirect(url_for('auth.login'))