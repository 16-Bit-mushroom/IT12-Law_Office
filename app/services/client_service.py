# app/services/client_service.py
from app.models import db
from app.models.client_mdl import Client

# app/services/client_service.py
from app.models import db
from app.models.client_mdl import Client

def add_client(data):
    """
    Add a new client (Normalized)
    Accepts a dictionary 'data' containing all form fields
    """
    try:
        # Create base object with shared fields
        client = Client(
            client_type=data.get('client_type', 'individual'),
            email=data.get('email'),
            phone=data.get('phone'),
            notes=data.get('notes'),
            
            # Atomic Address
            street_address=data.get('street_address'),
            barangay=data.get('barangay'),
            city=data.get('city'),
            province=data.get('province'),
            zip_code=data.get('zip_code')
        )

        # Conditional Logic based on Type
        if client.client_type == 'individual':
            client.first_name = data.get('first_name')
            client.middle_name = data.get('middle_name')
            client.last_name = data.get('last_name')
            # client.date_of_birth = ... (if you add date parsing)
            
        elif client.client_type == 'corporate':
            client.company_name = data.get('company_name')
            client.company_reg_number = data.get('company_reg_number')
            client.tax_identification_number = data.get('tax_id')
            client.designated_representative = data.get('representative')

        db.session.add(client)
        db.session.commit()
        return client
        
    except Exception as e:
        db.session.rollback()
        raise e

def get_all_clients():
    """Get all active clients (exclude recycle bin)"""
    # UPDATED: Filter where deleted_at is NULL
    return Client.query.filter(Client.deleted_at == None).order_by(Client.id.desc()).all()

def get_client_by_id(client_id):
    """Get client by ID"""
    return Client.query.get(client_id)

def get_client_by_email(email):
    """Get client by email"""
    return Client.query.filter_by(email=email).first()

def delete_client(client_id):
    """Soft delete a client"""
    try:
        client = Client.query.get(client_id)
        if client:
            client.soft_delete() # Uses Mixin
            return True
        return False
    except Exception as e:
        db.session.rollback()
        raise e