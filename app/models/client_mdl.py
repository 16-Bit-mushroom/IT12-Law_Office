# app/models/client_mdl.py
from . import db
from datetime import datetime
from app.utils.mixins import SoftDeleteMixin

class Client(db.Model, SoftDeleteMixin):
    __tablename__ = 'clients'

    id = db.Column(db.Integer, primary_key=True)
    
    # 1. DISCRIMINATOR
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
    
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    # --- SMART PROPERTIES ---

    @property
    def update_details(self, form_data):
        """Updates client details safely from form data"""
        # Map form fields to model fields
        if self.client_type == 'individual':
            self.first_name = form_data.get('first_name', self.first_name)
            self.middle_name = form_data.get('middle_name', self.middle_name)
            self.last_name = form_data.get('last_name', self.last_name)
        else:
            self.company_name = form_data.get('company_name', self.company_name)
            self.designated_representative = form_data.get('representative', self.designated_representative)
            
        self.email = form_data.get('email', self.email)
        self.phone = form_data.get('phone', self.phone)
        self.street_address = form_data.get('street_address', self.street_address)
        self.city = form_data.get('city', self.city)
        self.province = form_data.get('province', self.province)
        self.zip_code = form_data.get('zip_code', self.zip_code)
        
        self.updated_at = datetime.now()
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