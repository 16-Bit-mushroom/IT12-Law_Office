from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from app.services.user_service import create_new_user, get_user_by_id, update_user_profile, update_user_password, get_all_users, update_user_profile_admin
from flask_login import login_required, current_user


# Renamed blueprint to 'admin' and prefix to '/' to serve the main admin page
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# --- Removed Helper Function (get_current_user_id_simulated) ---
# We now rely solely on Flask-Login's 'current_user' proxy object, which is available 
# because of the @login_required decorator.

@admin_bp.route('/', methods=['GET'])
@login_required
def admin_page():
    # current_user is available due to @login_required and holds the full User object
    # loaded by the user_loader function in __init__.py.
    
    # NOTE: Since the current_user proxy object is available and holds the data, 
    # we don't need to manually fetch the user via get_user_by_id(current_user.id)
    # unless you specifically need to load the user fresh from the database (e.g., after an update).
    # For a simple GET request, the proxy is usually sufficient.
    
    # Render the template with the current user data
    return render_template('manage_profile_page.html', current_user=current_user)

@admin_bp.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    # Ensure current_user is authenticated before attempting updates.
    if not current_user.is_authenticated:
        flash('Authentication required to update profile.', 'danger')
        # Redirect to the main login/admin page for the error to show up
        return redirect(url_for('admin.admin_page')) 

    user_id = current_user.id
    
    # --- 1. Handle General Info Update ---
    username = request.form['username']
    email = request.form['email']
    
    # Perform update if either field has changed
    if current_user.username != username or current_user.email != email:
        success, message = update_user_profile(user_id, username, email)
        if success:
            flash(message, 'success')
        else:
            flash(f"Profile update failed: {message}", 'danger')

    # --- 2. Handle Password Change (if passwords are provided) ---
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')

    if new_password: # Only proceed if the user intended to change the password
        # current_user is a proxy, but the underlying User object should have check_password
        if not current_user.check_password(current_password):
            flash('Password change failed: Current password is incorrect.', 'danger')
        elif new_password != confirm_password:
            flash('Password change failed: New password and confirmation do not match.', 'danger')
        else:
            # Check password strength/length (basic check)
            if len(new_password) < 8:
                 flash('Password change failed: New password must be at least 8 characters.', 'danger')
            else:
                pw_success, pw_message = update_user_password(user_id, new_password)
                if pw_success:
                    flash(pw_message, 'success')
                else:
                    flash(f"Password update failed: {pw_message}", 'danger')
    
    # Redirect back to the profile page to see the changes/messages
    return redirect(url_for('admin.admin_page'))

@admin_bp.route('/users')
@login_required
def manage_users_page():
    """Renders the page to view and manage all system users/employees."""
    
    # Check if the authenticated user is an admin
    # 'current_user' is now imported and defined.
    # 'abort' is now imported and defined.
    if not current_user.is_admin:
        abort(403) # Forbidden
        
    # 'get_all_users' is now imported from user_service.
    users = get_all_users()
    
    return render_template('manage_users.html', users=users)

@admin_bp.route('/users/new', methods=['GET', 'POST'])
@login_required
def add_new_user():
    """Handles adding a new user to the system."""
    if not current_user.is_admin:
        abort(403)  # Forbidden
    
    if request.method == 'POST':
        # Get form data
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        is_admin = 'is_admin' in request.form  # Checkbox returns 'on' if checked
        
        # Basic validation
        if not username or not email or not password:
            flash('All fields are required.', 'danger')
            return render_template('add_user.html')
        
        if len(password) < 8:
            flash('Password must be at least 8 characters long.', 'danger')
            return render_template('add_user.html')
        
        # Create new user
        success, message = create_new_user(username, email, password, is_admin)
        
        if success:
            flash(message, 'success')
            return redirect(url_for('admin.manage_users_page'))
        else:
            flash(f'Failed to create user: {message}', 'danger')
            return render_template('add_user.html')
    
    return render_template('add_user.html')

@admin_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    """Handles editing an existing user."""
    if not current_user.is_admin:
        abort(403)  # Forbidden
    
    user = get_user_by_id(user_id)
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('admin.manage_users_page'))
    
    if request.method == 'POST':
        # Get form data
        username = request.form.get('username')
        email = request.form.get('email')
        is_admin = 'is_admin' in request.form
        new_password = request.form.get('new_password')
        
        # Update user profile (username, email, admin status)
        success, message = update_user_profile_admin(
            user_id, username, email, is_admin
        )
        
        if success:
            flash('Profile updated successfully.', 'success')
        else:
            flash(f'Profile update failed: {message}', 'danger')
            return render_template('edit_user.html', user=user)
        
        # Update password if provided
        if new_password:
            if len(new_password) < 8:
                flash('Password must be at least 8 characters long.', 'danger')
            else:
                pw_success, pw_message = update_user_password(user_id, new_password)
                if pw_success:
                    flash('Password updated successfully.', 'success')
                else:
                    flash(f'Password update failed: {pw_message}', 'danger')
        
        return redirect(url_for('admin.manage_users_page'))
    
    return render_template('edit_user.html', user=user)