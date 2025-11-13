from app.models import db
from app.models.service_mdl import Service

def get_all_services():
    """Get all services"""
    return Service.query.all()

def get_service_by_id(service_id):
    """Get service by ID"""
    return Service.query.get(service_id)

def create_service(service_data):
    """Create a new service"""
    try:
        service = Service(
            service_name=service_data.get('service_name'),
            fee=service_data.get('fee'),
            description=service_data.get('description')
        )
        db.session.add(service)
        db.session.commit()
        return service
    except Exception as e:
        db.session.rollback()
        raise e

def update_service(service_id, service_data):
    """Update an existing service"""
    try:
        service = Service.query.get(service_id)
        if service:
            service.service_name = service_data.get('service_name', service.service_name)
            service.fee = service_data.get('fee', service.fee)
            service.description = service_data.get('description', service.description)
            db.session.commit()
        return service
    except Exception as e:
        db.session.rollback()
        raise e

def delete_service(service_id):
    """Delete a service"""
    try:
        service = Service.query.get(service_id)
        if service:
            db.session.delete(service)
            db.session.commit()
        return True
    except Exception as e:
        db.session.rollback()
        raise e