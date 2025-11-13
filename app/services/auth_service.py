from app.models import db
from app.models.user_model import User
from app.models.service_mdl import Service
from sqlalchemy import Numeric
from flask_login import login_user, logout_user, current_user

def seed_initial_admin():
    """Seed the initial admin user and services if they don't exist"""
    # Seed admin user
    if User.query.first() is None:
        admin = User(
            username='admin',
            email='admin@lawoffice.com',
            role='admin',
            is_admin=True
        )
        admin.set_password('password123')
        db.session.add(admin)
        db.session.commit()
        print("--- Initial Admin User SEEDED: Username 'admin', Password 'password123' ---")
        print("--- PLEASE CHANGE THIS PASSWORD IMMEDIATELY AFTER FIRST LOGIN ---")

    # Seed initial services
    if Service.query.first() is None:
        services = [
            Service(
                service_name='Notarization',
                fee=100.00,
                description='Document notarization service'
            ),
            Service(
                service_name='Affidavit Preparation',
                fee=150.00,
                description='Preparation and notarization of affidavits'
            ),
            Service(
                service_name='Special Power of Attorney',
                fee=200.00,
                description='SPA document preparation and notarization'
            ),
            Service(
                service_name='Deed of Sale',
                fee=300.00,
                description='Deed of Sale preparation and notarization'
            ),
            Service(
                service_name='Contract Review',
                fee=250.00,
                description='Legal contract review and consultation'
            ),
            Service(
                service_name='Legal Consultation',
                fee=500.00,
                description='General legal consultation service'
            )
        ]
        
        db.session.add_all(services)
        db.session.commit()
        print("--- Initial Services SEEDED ---")

def authenticate_user(email, password):
    """Authenticate a user by email and password"""
    user = User.query.filter_by(email=email).first()
    if user and user.check_password(password):
        login_user(user)
        return True, user
    return False, "Invalid email or password"

def deauthenticate_user():
    """Log out the current user"""
    logout_user()
    return "You have been logged out successfully."