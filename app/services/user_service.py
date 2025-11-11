from app.models.user_model import db, User
from sqlalchemy.exc import SQLAlchemyError
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

def get_user_by_id(user_id):
    """
    Retrieves a user object by their primary key ID.
    
    In a real Flask application with Flask-Login, you'd typically use 
    'current_user' from the context, but this function provides the
    underlying service layer capability.
    """
    try:
        user = db.session.get(User, user_id)
        return user
    except SQLAlchemyError as e:
        logging.error(f"Error fetching user ID {user_id}: {e}")
        
        return None
def get_all_users():
    try:
        return User.query.all()
    except SQLAlchemyError as e:
        logging.error(f"Error fetching all users: {e}")
        return []


def update_user_profile(user_id, username, email):
    """
    Updates the general information (username and email) for a user.
    """
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
        db.session.commit()
        return True, "Profile updated successfully."

    except SQLAlchemyError as e:
        db.session.rollback()
        logging.error(f"Error updating profile for user ID {user_id}: {e}")
        return False, "A database error occurred during profile update."

def update_user_password(user_id, new_password):
    """
    Updates the password for a user.
    """
    try:
        user = db.session.get(User, user_id)
        if not user:
            return False, "User not found."
        
        # Use the set_password method from the User model to hash the new password
        user.set_password(new_password)
        db.session.commit()
        return True, "Password updated successfully."

    except SQLAlchemyError as e:
        db.session.rollback()
        logging.error(f"Error updating password for user ID {user_id}: {e}")
        return False, "A database error occurred during password update."

def create_new_user(username, email, password, is_admin=False):
    """
    Creates a new user in the system.
    """
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

def update_user_profile_admin(user_id, username, email, is_admin):
    """
    Updates user profile information (admin version - includes role changes).
    """
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
        user.is_admin = is_admin
        
        db.session.commit()
        return True, "Profile updated successfully."

    except SQLAlchemyError as e:
        db.session.rollback()
        logging.error(f"Error updating profile for user ID {user_id}: {e}")
        return False, "A database error occurred during profile update."