# app/services/client_service.py
from app.models import db
from app.models.client_mdl import Client

def add_client(address, email, phone, role, notes, first_name, last_name):
    """Add a new client"""
    try:
        client = Client(
            client_first_name=first_name,
            client_last_name=last_name,
            client_address=address,
            client_email=email,
            client_phone=phone,
            client_role=role,
            notes=notes
        )
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
    return Client.query.filter_by(client_email=email).first()

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