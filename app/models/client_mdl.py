# app/models/client_mdl.py
from . import db
from datetime import datetime
from app.utils.mixins import SoftDeleteMixin

class Client(db.Model, SoftDeleteMixin):
    __tablename__ = 'clients'

    id = db.Column(db.Integer, primary_key=True)
    
    # 1. DISCRIMINATOR
    # 'individual' or 'corporate'
    client_type = db.Column(db.String(20), default='individual', nullable=False) 
    
    # 2. INDIVIDUAL FIELDS (Nullable)
    first_name = db.Column(db.String(100), nullable=True)
    middle_name = db.Column(db.String(100), nullable=True)
    last_name = db.Column(db.String(100), nullable=True)
    date_of_birth = db.Column(db.Date, nullable=True)
    
    # 3. CORPORATE FIELDS (Nullable)
    company_name = db.Column(db.String(200), nullable=True)
    company_reg_number = db.Column(db.String(100), nullable=True) # SEC/DTI No.
    tax_identification_number = db.Column(db.String(50), nullable=True) # TIN
    designated_representative = db.Column(db.String(150), nullable=True) # Contact Person
    
    # 4. ATOMIC ADDRESS (Shared)
    street_address = db.Column(db.String(255), nullable=True) # House No, Street, Subd
    barangay = db.Column(db.String(100), nullable=True)
    city = db.Column(db.String(100), nullable=True)
    province = db.Column(db.String(100), nullable=True)
    zip_code = db.Column(db.String(10), nullable=True)
    
    # 5. CONTACT (Shared)
    email = db.Column(db.String(120), nullable=False) # Unique identifier
    phone = db.Column(db.String(50), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    
    # Meta
    is_active = db.Column(db.Boolean, default=True)
    deleted_at = db.Column(db.DateTime, nullable=True)

    # --- SMART PROPERTIES ---

    @property
    def full_name(self):
        """Returns the display name based on type"""
        if self.client_type == 'corporate':
            return self.company_name or "Unnamed Corporation"
        else:
            # Handle Middle Initial logic
            mi = f" {self.middle_name[0]}." if self.middle_name else ""
            return f"{self.first_name}{mi} {self.last_name}"

    @property
    def full_address(self):
        """Reconstructs the full address string"""
        parts = [
            self.street_address,
            self.barangay,
            self.city,
            self.province,
            self.zip_code
        ]
        # Filter out None/Empty parts and join with comma
        return ", ".join([p for p in parts if p])

    def __repr__(self):
        return f"<Client({self.client_type}, id={self.id}, name='{self.full_name}')>"