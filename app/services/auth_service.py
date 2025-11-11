from app.models import db  # This should now work correctly
from app.models.user_model import User
from sqlalchemy.exc import SQLAlchemyError
from flask_login import login_user, logout_user
import logging

logging.basicConfig(level=logging.INFO)

def seed_initial_admin():
    """
    Ensures at least one admin user exists in the database.
    This is critical for the first run of the application.
    """
    try:
        if not User.query.filter_by(is_admin=True).first():
            admin_user = User(
                username='admin',
                email='admin@rjb-law.com',
                role='senior partner',
                is_admin=True
            )
            # Default secure password for initial login: 'password123'
            admin_user.set_password('password123') 
            
            db.session.add(admin_user)
            db.session.commit()
            logging.warning("--- Initial Admin User SEEDED: Username 'admin', Password 'password123' ---")
            logging.warning("--- PLEASE CHANGE THIS PASSWORD IMMEDIATELY AFTER FIRST LOGIN ---")
    except SQLAlchemyError as e:
        db.session.rollback()
        logging.error(f"Error seeding initial admin user: {e}")

def authenticate_user(email, password):
    """
    Authenticates a user based on email and password.
    If successful, logs the user in via Flask-Login.
    """
    try:
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            # Log the user in with Flask-Login
            login_user(user, remember=True)
            return True, user
        
        return False, "Invalid email or password."
    except SQLAlchemyError as e:
        logging.error(f"Database error during authentication: {e}")
        return False, "A database error occurred."

def deauthenticate_user():
    """Logs the currently logged-in user out."""
    logout_user()
    return "You have been logged out."