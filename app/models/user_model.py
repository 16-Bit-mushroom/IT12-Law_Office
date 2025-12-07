# user_model.py
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from . import db

class User(UserMixin, db.Model):
    """
    User model for authentication and authorization in the application.
    This includes fields necessary for user management (Admin functionality).
    """
    __tablename__ = 'users'

    # Core identification fields
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    
    # Security field - Stores the hashed password, NOT the plain text password
    password_hash = db.Column(db.String(128), nullable=False)
    
    # Contact Information
    contact_number = db.Column(db.String(20), nullable=True)
    
    # Authorization and Status fields
    # Role: Determines access level (e.g., 'admin', 'attorney', 'paralegal')
    role = db.Column(db.String(50), default='attorney', nullable=False)
    # Status: For disabling/enabling accounts without deleting them
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    # Admin flag
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # --- Methods for Password Security ---
    def set_password(self, password):
        """Hashes the plain text password for secure storage."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Checks the provided plain text password against the stored hash."""
        return check_password_hash(self.password_hash, password)

    # --- Methods for Admin Functionality ---
    def disable(self):
        """Sets the user's active status to False."""
        self.is_active = False

    def enable(self):
        """Sets the user's active status to True."""
        self.is_active = True

    def to_dict(self):
        """Convert user object to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'contact_number': self.contact_number,
            'role': self.role,
            'is_admin': self.is_admin,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f"<User {self.username} | Role: {self.role}>"
    
    
    # ... inside class User ...

    @property
    def full_name(self):
        """Helper to return username as full name for now"""
        return self.username