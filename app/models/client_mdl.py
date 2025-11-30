from . import db
from datetime import datetime

class Client(db.Model):
    __tablename__ = 'clients'

    id = db.Column(db.Integer, primary_key=True)
    client_first_name = db.Column(db.String(100), nullable=False)
    client_last_name = db.Column(db.String(100), nullable=False)
    client_address = db.Column(db.String(255), nullable=False) 
    client_email = db.Column(db.String(120), nullable=False, unique=True)
    client_phone = db.Column(db.String(50))
    client_role = db.Column(db.String(50))
    notes = db.Column(db.Text)
    
    # ADD SOFT DELETE FIELDS
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    deleted_at = db.Column(db.DateTime, nullable=True)


    # Property to get full name
    @property
    def full_name(self):
        return f"{self.client_first_name} {self.client_last_name}"

    # ADD SOFT DELETE METHODS
    def soft_delete(self):
        """Soft delete the client - move to recycle bin"""
        self.is_active = False
        self.deleted_at = datetime.utcnow()

    def restore(self):
        """Restore client from recycle bin"""
        self.is_active = True
        self.deleted_at = None

    def __repr__(self):
        return f"<Client(id={self.id}, name='{self.full_name}', email='{self.client_email}')>"