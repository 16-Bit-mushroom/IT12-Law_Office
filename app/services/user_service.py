# user_service.py
from app.models.user_model import db, User
from sqlalchemy.exc import SQLAlchemyError
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

def get_user_by_id(user_id):
    """Retrieves a user object by their primary key ID."""
    try:
        user = db.session.get(User, user_id)
        return user
    except SQLAlchemyError as e:
        logging.error(f"Error fetching user ID {user_id}: {e}")
        return None

def get_all_users():
    """Get all users"""
    try:
        return User.query.all()
    except SQLAlchemyError as e:
        logging.error(f"Error fetching all users: {e}")
        return []

def get_active_users():
    """Get only active users"""
    try:
        return User.query.filter_by(is_active=True).all()
    except SQLAlchemyError as e:
        logging.error(f"Error fetching active users: {e}")
        return []

def update_user_profile(user_id, username, email, contact_number):
    """Updates the general information for a user."""
    try:
        user = db.session.get(User, user_id)
        if not user:
            return False, "User not found."
            
        # Check for unique constraints before updating
        if user.username != username and User.query.filter_by(username=username).first():
            return False, "Username is already taken."
        
        if user.email != email and User.query.filter_by(email=email).first():
            return False, "Email is already in use."

        user.username = username
        user.email = email
        user.contact_number = contact_number
        db.session.commit()
        return True, "Profile updated successfully."

    except SQLAlchemyError as e:
        db.session.rollback()
        logging.error(f"Error updating profile for user ID {user_id}: {e}")
        return False, "A database error occurred during profile update."

def update_user_password(user_id, new_password):
    """Updates the password for a user."""
    try:
        user = db.session.get(User, user_id)
        if not user:
            return False, "User not found."
        
        user.set_password(new_password)
        db.session.commit()
        return True, "Password updated successfully."

    except SQLAlchemyError as e:
        db.session.rollback()
        logging.error(f"Error updating password for user ID {user_id}: {e}")
        return False, "A database error occurred during password update."

def create_new_user(username, email, password, contact_number=None, role='attorney', is_admin=False):
    """Creates a new user in the system."""
    try:
        # Check if username or email already exists
        if User.query.filter_by(username=username).first():
            return False, "Username is already taken."
        
        if User.query.filter_by(email=email).first():
            return False, "Email is already in use."

        # Create new user
        user = User(
            username=username,
            email=email,
            contact_number=contact_number,
            role=role,
            is_admin=is_admin
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        return True, "User created successfully."

    except SQLAlchemyError as e:
        db.session.rollback()
        logging.error(f"Error creating new user {username}: {e}")
        return False, "A database error occurred during user creation."

# In app/services/user_service.py

def update_user_profile_admin(user_id, data):
    """Updates user profile information (admin version)."""
    try:
        user = db.session.get(User, user_id)
        if not user:
            return False, "User not found."
            
        # Check uniqueness only if changed
        if data.get('username') and user.username != data['username']:
            if User.query.filter_by(username=data['username']).first():
                return False, "Username is already taken."
        
        if data.get('email') and user.email != data['email']:
            if User.query.filter_by(email=data['email']).first():
                return False, "Email is already in use."

        # Apply Updates
        user.username = data.get('username', user.username)
        user.email = data.get('email', user.email)
        user.contact_number = data.get('contact_number', user.contact_number)
        user.role = data.get('role', user.role)
        
        # Boolean fields
        user.is_admin = data.get('is_admin', user.is_admin)
        user.is_active = data.get('is_active', user.is_active)

        # === NEW FIELDS ===
        user.first_name = data.get('first_name', user.first_name)
        user.middle_name = data.get('middle_name', user.middle_name)
        user.last_name = data.get('last_name', user.last_name)
        user.gender = data.get('gender', user.gender)
        user.address = data.get('address', user.address)
        
        # Handle Date
        if data.get('birth_date'):
            from datetime import datetime
            if isinstance(data['birth_date'], str):
                user.birth_date = datetime.strptime(data['birth_date'], '%Y-%m-%d').date()
            else:
                user.birth_date = data['birth_date']
        # ==================
        
        db.session.commit()
        return True, "Profile updated successfully."

    except SQLAlchemyError as e:
        db.session.rollback()
        logging.error(f"Error updating profile for user ID {user_id}: {e}")
        return False, f"Database error: {str(e)}"

def delete_user(user_id):
    """Soft deletes a user by setting is_active to False."""
    try:
        user = db.session.get(User, user_id)
        if not user:
            return False, "User not found."
        
        user.is_active = False
        db.session.commit()
        return True, "User deactivated successfully."

    except SQLAlchemyError as e:
        db.session.rollback()
        logging.error(f"Error deactivating user ID {user_id}: {e}")
        return False, "A database error occurred during user deactivation."

def activate_user(user_id):
    """Reactivates a user by setting is_active to True."""
    try:
        user = db.session.get(User, user_id)
        if not user:
            return False, "User not found."
        
        user.is_active = True
        db.session.commit()
        return True, "User activated successfully."

    except SQLAlchemyError as e:
        db.session.rollback()
        logging.error(f"Error activating user ID {user_id}: {e}")
        return False, "A database error occurred during user activation."